"""Application commands for resolving Agent Run approvals."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.impl.sqlite_agent_approval_repo import SqliteAgentApprovalRepository
from app.repositories.impl.sqlite_agent_fact_repo import SqliteAgentToolCallRepository
from app.repositories.impl.sqlite_agent_run_repo import SqliteAgentRunRepository
from app.services.agent_approval_service import AgentApprovalError, AgentApprovalService
from app.services.agent_run_service import AgentRunService


@dataclass(frozen=True)
class ResolveApprovalCommand:
    run_id: str
    checkpoint_ref: str
    user_id: str
    decision: str
    edited_arguments: dict | None
    argument_diff: list | None
    rejection_message: str | None
    resume_payload: dict


class AgentApprovalCommands:
    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def resolve(self, command: ResolveApprovalCommand) -> list[dict]:
        async with self._session_maker() as session:
            try:
                items = await AgentApprovalService(
                    SqliteAgentApprovalRepository(session)
                ).claim(
                    run_id=command.run_id,
                    checkpoint_ref=command.checkpoint_ref,
                    user_id=command.user_id,
                    decision=command.decision,
                    edited_arguments=command.edited_arguments,
                    argument_diff=command.argument_diff,
                    rejection_message=command.rejection_message,
                    claimed_by=command.user_id,
                )
                if command.decision == "reject":
                    tool_repo = SqliteAgentToolCallRepository(session)
                    for item in items:
                        await tool_repo.reject_before_execution(
                            tool_call_id=str(item.get("tool_call_id") or ""),
                            reason=command.rejection_message,
                        )
                await AgentRunService(SqliteAgentRunRepository(session)).enqueue_resume(
                    command.run_id,
                    command.user_id,
                    command.resume_payload,
                )
                await session.commit()
                return items
            except AgentApprovalError:
                await session.commit()
                raise
            except Exception:
                await session.rollback()
                raise
