from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.agent.reconciliation import AgentStateReconciler
from app.models.agent_run import AgentRun
from app.models.agent_run_event import AgentRunEvent
from app.models.agent_session import AgentSession
from app.models.agent_session_lease import AgentSessionLease
from app.models.session_state import SessionState


def test_reconciliation_dry_run_apply_and_idempotency() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        cutoff = datetime.utcnow() - timedelta(minutes=30)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(AgentSession.__table__.create)
                await conn.run_sync(AgentRun.__table__.create)
                await conn.run_sync(AgentRunEvent.__table__.create)
                await conn.run_sync(AgentSessionLease.__table__.create)
                await conn.run_sync(SessionState.__table__.create)
            async with sessions() as session:
                session.add_all(
                    [
                        AgentSession(session_id="stale_session", user_id="user_1", title="stale", status="active"),
                        AgentSession(session_id="fresh_session", user_id="user_1", title="fresh", status="active"),
                        AgentSession(session_id="approval_session", user_id="user_1", title="approval", status="active"),
                        AgentRun(
                            run_id="stale_run",
                            session_id="stale_session",
                            user_id="user_1",
                            status="running",
                            input_text="old",
                            started_at=cutoff - timedelta(minutes=1),
                        ),
                        AgentRun(
                            run_id="fresh_run",
                            session_id="fresh_session",
                            user_id="user_1",
                            status="running",
                            input_text="new",
                            started_at=cutoff + timedelta(minutes=1),
                        ),
                        AgentRun(
                            run_id="approval_run",
                            session_id="approval_session",
                            user_id="user_1",
                            status="requires_action",
                            input_text="approve",
                            started_at=cutoff - timedelta(hours=1),
                        ),
                        SessionState(session_id="stale_session", user_id="user_1", status="running"),
                        SessionState(session_id="fresh_session", user_id="user_1", status="running"),
                        SessionState(session_id="approval_session", user_id="user_1", status="running"),
                        SessionState(session_id="orphan_session", user_id="user_1", status="running"),
                    ]
                )
                await session.commit()

            async with sessions() as session:
                dry_run = await AgentStateReconciler(session).reconcile(cutoff=cutoff, apply=False)
                await session.rollback()
                assert dry_run.dry_run is True
                assert len(dry_run.actions) == 4
                stale = await session.get(AgentRun, "stale_run")
                assert stale is not None and stale.status == "running"

            async with sessions() as session:
                applied = await AgentStateReconciler(session).reconcile(cutoff=cutoff, apply=True)
                await session.commit()
                assert applied.dry_run is False
                assert applied.conflicts == 0

            async with sessions() as session:
                stale = await session.get(AgentRun, "stale_run")
                stale_state = await session.get(SessionState, "stale_session")
                fresh = await session.get(AgentRun, "fresh_run")
                fresh_state = await session.get(SessionState, "fresh_session")
                approval_state = await session.get(SessionState, "approval_session")
                orphan_state = await session.get(SessionState, "orphan_session")
                assert stale is not None and stale.status == "error"
                terminal_event = await session.get(AgentRunEvent, stale.terminal_event_id)
                assert terminal_event is not None and terminal_event.event_type == "run.error"
                assert stale_state is not None and stale_state.status == "error"
                assert fresh is not None and fresh.status == "running"
                assert fresh_state is not None and fresh_state.status == "running"
                assert approval_state is not None and approval_state.status == "active"
                assert orphan_state is not None and orphan_state.status == "active"

                repeated = await AgentStateReconciler(session).reconcile(cutoff=cutoff, apply=True)
                await session.commit()
                assert repeated.actions == []
                assert repeated.conflicts == 0
        finally:
            await engine.dispose()

    asyncio.run(scenario())
