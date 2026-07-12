from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config.database import Base
from app.repositories.impl.sqlite_agent_fact_repo import SqliteAgentToolCallRepository
from app.agent.services.message_assembler import ChatEventAssembler


def test_rejected_tool_fact_is_terminal_and_not_overwritten() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            repo = SqliteAgentToolCallRepository(session)
            await repo.upsert_started(
                run_id="run_1",
                tool_call_id="call_1",
                tool_name="update_campaign_status",
                arguments={"status": "running"},
            )
            await repo.reject_before_execution(tool_call_id="call_1", reason="keep paused")
            await repo.complete(tool_call_id="call_1", result={"sdk": "rejected"})
            facts = await repo.list_by_run("run_1")

        await engine.dispose()
        assert facts[0]["status"] == "rejected_before_execution"
        assert facts[0]["result"] == {
            "execution_outcome": "rejected_before_execution",
            "reason": "keep paused",
        }
        assert facts[0]["completed_at"] is not None

    asyncio.run(scenario())


def test_tool_output_uses_persisted_name_and_rejection_status() -> None:
    events = [
        (
            "run_item_stream_event",
            {
                "type": "run_item_stream_event",
                "name": "tool_output",
                "item": {
                    "raw_item": {"call_id": "call_1", "output": "rejected"},
                },
            },
        )
    ]
    content = ChatEventAssembler().assemble_assistant_message(
        events,
        tool_facts_by_id={
            "call_1": {
                "tool_name": "update_campaign_status",
                "arguments": {"status": "running"},
                "status": "rejected_before_execution",
                "result": {
                    "execution_outcome": "rejected_before_execution",
                    "reason": "keep paused",
                },
            }
        },
    )

    assert content["blocks"] == [
        {
            "type": "tool_call",
            "toolCallId": "call_1",
            "tool": "update_campaign_status",
            "args": {"status": "running"},
            "status": "rejected_before_execution",
            "result": {
                "execution_outcome": "rejected_before_execution",
                "reason": "keep paused",
            },
        }
    ]
