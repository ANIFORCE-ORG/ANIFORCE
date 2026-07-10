from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

backend_root = Path(__file__).parent.parent
project_root = backend_root.parent
sys.path.insert(0, str(backend_root))

from app.models.agent_run import AgentRun
from app.models.agent_run_event import AgentRunEvent
from app.repositories.impl.sqlite_agent_run_repo import SqliteAgentRunRepository
from app.services.agent_run_service import AgentRunService


def test_persistent_event_sequence_and_terminal_marker() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(AgentRun.__table__.create)
                await conn.run_sync(AgentRunEvent.__table__.create)
            async with sessions() as session:
                service = AgentRunService(SqliteAgentRunRepository(session))
                await service.repo.create(
                    run_id="run_sequence",
                    session_id="session_1",
                    user_id="user_1",
                    input_text="hello",
                )
                await service.mark_running("run_sequence", "user_1")
                paused = await service.mark_requires_action("run_sequence", "user_1", "ckpt_1")
                resumed = await service.mark_running("run_sequence", "user_1")
                completed = await service.mark_completed("run_sequence", "user_1")
                await session.commit()

                events = (
                    await session.execute(
                        AgentRunEvent.__table__.select()
                        .where(AgentRunEvent.run_id == "run_sequence")
                        .order_by(AgentRunEvent.sequence)
                    )
                ).mappings().all()

            assert paused is not None and paused["terminal_event_id"] is None
            assert resumed is not None and resumed["status"] == "running"
            assert completed is not None and completed["last_event_sequence"] == 4
            assert [event["event_type"] for event in events] == [
                "run.started",
                "run.requires_action",
                "run.resuming",
                "run.completed",
            ]
            assert [event["sequence"] for event in events] == [1, 2, 3, 4]
            assert [event["is_terminal"] for event in events] == [False, False, False, True]
            assert completed["terminal_event_id"] == events[-1]["id"]
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_concurrent_terminal_transitions_commit_only_one_status() -> None:
    async def scenario() -> None:
        db_path = project_root / "drafts" / "260710" / "260710_04_run_terminal_test.db"
        db_path.unlink(missing_ok=True)
        db_url = f"sqlite+aiosqlite:///{db_path}"
        first_engine = create_async_engine(db_url, connect_args={"timeout": 5})
        second_engine = create_async_engine(db_url, connect_args={"timeout": 5})
        first_sessions = async_sessionmaker(first_engine, expire_on_commit=False)
        second_sessions = async_sessionmaker(second_engine, expire_on_commit=False)
        try:
            async with first_engine.begin() as conn:
                await conn.run_sync(AgentRun.__table__.create)
                await conn.run_sync(AgentRunEvent.__table__.create)
            async with first_sessions() as session:
                await SqliteAgentRunRepository(session).create(
                    run_id="run_1",
                    session_id="session_1",
                    user_id="user_1",
                    input_text="hello",
                )
                await session.commit()

            async def mark_completed() -> str:
                async with first_sessions() as session:
                    run = await AgentRunService(SqliteAgentRunRepository(session)).mark_completed(
                        "run_1", "user_1"
                    )
                    await session.commit()
                    assert run is not None
                    return run["status"]

            async def mark_error() -> str:
                async with second_sessions() as session:
                    run = await AgentRunService(SqliteAgentRunRepository(session)).mark_error(
                        "run_1", "user_1", {"code": "FAILED"}
                    )
                    await session.commit()
                    assert run is not None
                    return run["status"]

            results = await asyncio.gather(mark_completed(), mark_error())
            async with first_sessions() as session:
                persisted = await SqliteAgentRunRepository(session).get("run_1", "user_1")

            assert persisted is not None
            assert persisted["status"] in {"completed", "error"}
            assert results == [persisted["status"], persisted["status"]]
            async with first_sessions() as session:
                events = (
                    await session.execute(
                        AgentRunEvent.__table__.select().where(AgentRunEvent.run_id == "run_1")
                    )
                ).mappings().all()
            assert len(events) == 1
            assert events[0]["is_terminal"] is True
            assert events[0]["id"] == persisted["terminal_event_id"]
            assert events[0]["sequence"] == 1
        finally:
            await first_engine.dispose()
            await second_engine.dispose()
            db_path.unlink(missing_ok=True)

    asyncio.run(scenario())
