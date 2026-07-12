"""Application commands for creating and cancelling product Agent Runs."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.factory import get_campaign_repo, get_material_repo, get_project_repo
from app.repositories.impl.sqlite_agent_message_repo import SqliteAgentMessageRepository
from app.repositories.impl.sqlite_agent_run_repo import SqliteAgentRunRepository
from app.repositories.impl.sqlite_agent_session_repo import SqliteAgentSessionRepository
from app.repositories.impl.sqlite_session_state_repo import SqliteSessionStateRepository
from app.services.agent_run_service import AgentRunService
from app.services.agent_session_service import AgentSessionService
from app.services.business_context_builder import BusinessContextBuilder
from app.services.chat_event_assembler import ChatEventAssembler


@dataclass(frozen=True)
class CreateRunCommand:
    user_id: str
    prompt: str
    requested_session_id: str | None
    task_type: str
    context_snapshot: dict | None
    idempotency_key: str | None


@dataclass(frozen=True)
class CreateRunResult:
    run: dict
    session_id: str
    reused: bool
    business_context_summary: str


class AgentRunCommands:
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def create(self, command: CreateRunCommand) -> CreateRunResult:
        async with self._session_maker() as session:
            try:
                session_service = AgentSessionService(
                    session_repo=SqliteAgentSessionRepository(session),
                    state_repo=SqliteSessionStateRepository(session),
                )
                if command.requested_session_id:
                    await session_service.require_active(
                        session_id=command.requested_session_id,
                        user_id=command.user_id,
                    )
                    session_id = command.requested_session_id
                else:
                    created = await session_service.create_session(
                        user_id=command.user_id,
                        title=command.prompt[:50] if command.prompt else "新对话",
                    )
                    session_id = created["session_id"]

                state_repo = SqliteSessionStateRepository(session)
                state = await state_repo.get(session_id, command.user_id)
                if not state:
                    state = await state_repo.create(session_id=session_id, user_id=command.user_id)
                changelog_start_index = len(state.get("changelog") or [])
                if command.context_snapshot is not None:
                    state = await state_repo.update_ui_snapshot(
                        session_id,
                        command.user_id,
                        state["version"],
                        command.context_snapshot,
                    )
                business_context = await BusinessContextBuilder(
                    project_repo=get_project_repo(session),
                    campaign_repo=get_campaign_repo(session),
                    material_repo=get_material_repo(session),
                ).build(state, command.user_id)
                run, reused = await AgentRunService(
                    SqliteAgentRunRepository(session)
                ).create_or_reuse(
                    session_id=session_id,
                    user_id=command.user_id,
                    input_text=command.prompt,
                    idempotency_key=command.idempotency_key,
                    execution_context={
                        "task_type": command.task_type,
                        "business_context_summary": business_context,
                        "ui_snapshot": command.context_snapshot or {},
                        "session_state": state,
                        "changelog_start_index": changelog_start_index,
                    },
                )
                if not reused:
                    await SqliteAgentMessageRepository(session).create(
                        session_id=session_id,
                        user_id=command.user_id,
                        role="user",
                        content_json=ChatEventAssembler().user_message(command.prompt),
                        run_id=run["run_id"],
                    )
                    await session_service.touch(session_id=session_id, user_id=command.user_id)
                await session.commit()
                return CreateRunResult(run, session_id, reused, business_context)
            except Exception:
                await session.rollback()
                raise
