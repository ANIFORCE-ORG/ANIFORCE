from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

backend_root = Path(__file__).parent.parent
project_root = backend_root.parent
sys.path.insert(0, str(backend_root))

from app.config.database import Base
from app.models import AgentRun, AgentSession, AgentSessionLease
from app.repositories.impl.sqlite_agent_run_repo import SqliteAgentRunRepository
from app.agent.runs.service import AgentRunService


def test_session_lease_and_terminal_fencing_across_engines() -> None:
    async def scenario() -> None:
        db_path = project_root / "drafts" / "260710" / f"260710_14_execution_fencing_{uuid4().hex}.db"
        db_path.unlink(missing_ok=True)
        engine_a = create_async_engine(f"sqlite+aiosqlite:///{db_path}", connect_args={"timeout": 5})
        engine_b = create_async_engine(f"sqlite+aiosqlite:///{db_path}", connect_args={"timeout": 5})
        maker_a = async_sessionmaker(engine_a, expire_on_commit=False)
        maker_b = async_sessionmaker(engine_b, expire_on_commit=False)
        try:
            async with engine_a.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            async with maker_a() as session:
                session.add(AgentSession(session_id="session_1", user_id="user_1", title="test", status="active"))
                session.add_all([
                    AgentRun(run_id="run_1", session_id="session_1", user_id="user_1", status="queued", input_text="one"),
                    AgentRun(run_id="run_2", session_id="session_1", user_id="user_1", status="queued", input_text="two"),
                ])
                await session.commit()

            async def claim(maker, owner):
                async with maker() as session:
                    item = await SqliteAgentRunRepository(session).claim_next(owner)
                    await session.commit()
                    return item

            first, second = await asyncio.gather(claim(maker_a, "worker-a"), claim(maker_b, "worker-b"))
            claimed = [item for item in (first, second) if item]
            assert len(claimed) == 1
            winner = claimed[0]
            owner = winner["lease_owner"]

            async with maker_b() as session:
                repo = SqliteAgentRunRepository(session)
                assert await repo.heartbeat(winner["run_id"], "stale-worker") is False
                stale = await AgentRunService(repo).mark_completed(
                    winner["run_id"], "user_1", final_output="stale", lease_owner="stale-worker"
                )
                await session.commit()
                assert stale and stale["status"] == "running"

            async with maker_a() as session:
                service = AgentRunService(SqliteAgentRunRepository(session))
                completed = await service.mark_completed(
                    winner["run_id"], "user_1", final_output="ok", lease_owner=owner
                )
                await session.commit()
                assert completed and completed["status"] == "completed"
                leases = (await session.execute(select(AgentSessionLease))).scalars().all()
                assert leases == []

            remaining = "run_2" if winner["run_id"] == "run_1" else "run_1"
            async with maker_b() as session:
                next_run = await SqliteAgentRunRepository(session).claim_next("worker-b")
                await session.commit()
                assert next_run and next_run["run_id"] == remaining
        finally:
            await engine_a.dispose()
            await engine_b.dispose()
            db_path.unlink(missing_ok=True)

    asyncio.run(scenario())
