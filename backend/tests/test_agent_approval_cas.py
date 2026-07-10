from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

backend_root = Path(__file__).parent.parent
project_root = backend_root.parent
sys.path.insert(0, str(backend_root))

from app.models.agent_approval import AgentApproval
from app.models.agent_run import AgentRun
from app.repositories.impl.sqlite_agent_approval_repo import SqliteAgentApprovalRepository
from app.repositories.impl.sqlite_agent_run_repo import SqliteAgentRunRepository
from app.services.agent_approval_service import AgentApprovalError, AgentApprovalService


async def _seed_approval(session, *, expires_at: datetime) -> None:
    await SqliteAgentRunRepository(session).create(
        run_id="run_1",
        session_id="session_1",
        user_id="user_1",
        input_text="create project",
        status="requires_action",
    )
    await AgentApprovalService(SqliteAgentApprovalRepository(session)).create_for_interruption(
        run_id="run_1",
        checkpoint_ref="ckpt_1",
        user_id="user_1",
        interruptions=[
            {
                "call_id": "call_1",
                "tool_name": "create_project",
                "arguments": '{"name":"demo"}',
            }
        ],
        expires_at=expires_at.isoformat(),
    )


def test_concurrent_approval_claim_has_one_winner() -> None:
    async def scenario() -> None:
        db_path = project_root / "drafts" / "260710" / "260710_10_approval_claim_test.db"
        db_path.unlink(missing_ok=True)
        db_url = f"sqlite+aiosqlite:///{db_path}"
        first_engine = create_async_engine(db_url, connect_args={"timeout": 5})
        second_engine = create_async_engine(db_url, connect_args={"timeout": 5})
        first_sessions = async_sessionmaker(first_engine, expire_on_commit=False)
        second_sessions = async_sessionmaker(second_engine, expire_on_commit=False)
        try:
            async with first_engine.begin() as conn:
                await conn.run_sync(AgentRun.__table__.create)
                await conn.run_sync(AgentApproval.__table__.create)
            async with first_sessions() as session:
                await _seed_approval(session, expires_at=datetime.utcnow() + timedelta(hours=1))
                await session.commit()

            async def claim(session_maker, decision: str):
                async with session_maker() as session:
                    service = AgentApprovalService(SqliteAgentApprovalRepository(session))
                    try:
                        result = await service.claim(
                            run_id="run_1",
                            checkpoint_ref="ckpt_1",
                            user_id="user_1",
                            decision=decision,
                            edited_arguments={"name": decision},
                            argument_diff=[],
                            rejection_message=None,
                        )
                        await session.commit()
                        return result
                    except AgentApprovalError as exc:
                        await session.rollback()
                        return exc

            first, second = await asyncio.gather(
                claim(first_sessions, "approve"),
                claim(second_sessions, "reject"),
            )
            assert sum(isinstance(item, list) for item in (first, second)) == 1
            conflicts = [item for item in (first, second) if isinstance(item, AgentApprovalError)]
            assert len(conflicts) == 1
            assert conflicts[0].code == "APPROVAL_CONFLICT"

            async with first_sessions() as session:
                rows = await SqliteAgentApprovalRepository(session).list_for_checkpoint(
                    "run_1", "ckpt_1", "user_1"
                )
            assert len(rows) == 1
            assert rows[0]["status"] == "resuming"
            assert rows[0]["version"] == 2
            assert rows[0]["tool_call_id"] == "call_1"
            assert rows[0]["tool_name"] == "create_project"
        finally:
            await first_engine.dispose()
            await second_engine.dispose()
            db_path.unlink(missing_ok=True)

    asyncio.run(scenario())


def test_expired_and_cross_user_approval_are_rejected() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(AgentRun.__table__.create)
                await conn.run_sync(AgentApproval.__table__.create)
            async with sessions() as session:
                await _seed_approval(session, expires_at=datetime.utcnow() - timedelta(seconds=1))
                await session.commit()

            async with sessions() as session:
                service = AgentApprovalService(SqliteAgentApprovalRepository(session))
                try:
                    await service.claim(
                        run_id="run_1",
                        checkpoint_ref="ckpt_1",
                        user_id="attacker",
                        decision="approve",
                        edited_arguments=None,
                        argument_diff=None,
                        rejection_message=None,
                    )
                except AgentApprovalError as exc:
                    assert exc.code == "APPROVAL_NOT_FOUND"
                    assert exc.status_code == 404
                else:
                    raise AssertionError("cross-user claim must fail")

                try:
                    await service.claim(
                        run_id="run_1",
                        checkpoint_ref="ckpt_1",
                        user_id="user_1",
                        decision="approve",
                        edited_arguments=None,
                        argument_diff=None,
                        rejection_message=None,
                    )
                except AgentApprovalError as exc:
                    assert exc.code == "APPROVAL_EXPIRED"
                    assert exc.status_code == 410
                else:
                    raise AssertionError("expired claim must fail")
                await session.commit()

            async with sessions() as session:
                rows = await SqliteAgentApprovalRepository(session).list_for_checkpoint(
                    "run_1", "ckpt_1", "user_1"
                )
            assert rows[0]["status"] == "expired"
        finally:
            await engine.dispose()

    asyncio.run(scenario())
