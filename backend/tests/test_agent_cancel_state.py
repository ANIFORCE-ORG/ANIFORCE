from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agent.runs.service import AgentRunService
from app.models.agent_run import AgentRun
from app.models.agent_run_event import AgentRunEvent
from app.repositories.impl.sqlite_agent_run_repo import SqliteAgentRunRepository


def test_cancel_settles_unclaimed_run_and_requests_running_cancel() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(AgentRun.__table__.create)
                await conn.run_sync(AgentRunEvent.__table__.create)
            async with sessions() as session:
                session.add_all([
                    AgentRun(
                        run_id="queued_run",
                        session_id="session_1",
                        user_id="user_1",
                        status="queued",
                        input_text="queued",
                    ),
                    AgentRun(
                        run_id="running_run",
                        session_id="session_2",
                        user_id="user_1",
                        status="running",
                        input_text="running",
                        lease_owner="worker_1",
                        lease_expires_at=datetime.utcnow() + timedelta(minutes=1),
                    ),
                ])
                await session.commit()

            async with sessions() as session:
                service = AgentRunService(SqliteAgentRunRepository(session))
                queued = await service.request_cancel("queued_run", "user_1")
                running = await service.request_cancel("running_run", "user_1")
                await session.commit()

                assert queued["status"] == "cancelled"
                assert queued["terminal_event_id"] is not None
                assert running["status"] == "cancel_requested"
                assert running["terminal_event_id"] is None
        finally:
            await engine.dispose()

    asyncio.run(scenario())
