from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

backend_root = Path(__file__).parent.parent
project_root = backend_root.parent
sys.path.insert(0, str(backend_root))

from app.models.agent_run import AgentRun
from app.repositories.impl.sqlite_agent_run_repo import SqliteAgentRunRepository
from app.services.agent_run_service import AgentRunService


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
        finally:
            await first_engine.dispose()
            await second_engine.dispose()
            db_path.unlink(missing_ok=True)

    asyncio.run(scenario())
