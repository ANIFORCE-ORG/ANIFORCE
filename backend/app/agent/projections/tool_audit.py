"""Project Runtime tool events into durable ToolCall audit facts."""

from app.repositories.impl.sqlite_agent_fact_repo import SqliteAgentToolCallRepository
from app.services.chat_event_assembler import ChatEventAssembler


class ToolAuditProjection:
    def __init__(self, repository: SqliteAgentToolCallRepository) -> None:
        self._repository = repository
        self._assembler = ChatEventAssembler()

    async def project(self, run_id: str, events: list[tuple[str, dict]]) -> None:
        for event_name, data in events:
            if event_name != "run_item_stream_event":
                continue
            if str(data.get("type") or "") not in {"", "run_item_stream_event"}:
                continue
            item = data.get("item") if isinstance(data.get("item"), dict) else {}
            if data.get("name") == "tool_called":
                call_id, tool_name, arguments = self._assembler._tool_call_info(item)
                if call_id:
                    await self._repository.upsert_started(
                        run_id=run_id,
                        tool_call_id=call_id,
                        tool_name=tool_name,
                        arguments=arguments,
                    )
            elif data.get("name") == "tool_output":
                call_id, result = self._assembler._tool_output_info(item)
                if call_id:
                    await self._repository.complete(tool_call_id=call_id, result=result)
