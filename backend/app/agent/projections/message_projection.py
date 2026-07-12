"""Project a terminal run into one durable assistant Message."""

from app.repositories.impl.sqlite_agent_fact_repo import SqliteAgentToolCallRepository
from app.repositories.impl.sqlite_agent_message_repo import SqliteAgentMessageRepository
from app.agent.services.message_assembler import ChatEventAssembler


class MessageProjection:
    def __init__(
        self,
        messages: SqliteAgentMessageRepository,
        tool_calls: SqliteAgentToolCallRepository,
    ) -> None:
        self._messages = messages
        self._tool_calls = tool_calls
        self._assembler = ChatEventAssembler()

    async def project_success(
        self,
        *,
        run_id: str,
        session_id: str,
        user_id: str,
        events: list[tuple[str, dict]],
    ) -> None:
        tool_facts = await self._tool_calls.list_by_run(run_id)
        content = self._assembler.assemble_assistant_message(
            events,
            tool_facts_by_id={item["tool_call_id"]: item for item in tool_facts},
        )
        await self._messages.create(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content_json=content,
            run_id=run_id,
        )

    async def project_error(
        self,
        *,
        run_id: str,
        session_id: str,
        user_id: str,
        error: dict,
    ) -> None:
        code = str(error.get("code") or "RUN_FAILED")
        await self._messages.create(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content_json=self._assembler.error_message(
                code,
                str(error.get("message") or "Agent run failed"),
            ),
            run_id=run_id,
            status="error",
            error_code=code,
        )
