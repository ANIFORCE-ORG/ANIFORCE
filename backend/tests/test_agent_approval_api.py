from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.api.v1 import agent_routes
from app.models.agent_approval import AgentApproval
from app.models.agent_run import AgentRun
from app.repositories.impl.sqlite_agent_approval_repo import SqliteAgentApprovalRepository
from app.repositories.impl.sqlite_agent_run_repo import SqliteAgentRunRepository
from app.services.agent_approval_service import AgentApprovalError, AgentApprovalService


class FakeRequest:
    headers = {"Authorization": "Bearer trusted-token"}

    def __init__(self, decision: str = "approve") -> None:
        self.decision = decision

    async def json(self) -> dict:
        return {
            "decision": self.decision,
            "edited_arguments": {"name": "approved"},
            "argument_diff": [{"field": "name", "new": "approved"}],
        }


class CountingGateway:
    def __init__(self, event_name: str = "runtime.completed") -> None:
        self.calls = 0
        self.event_name = event_name

    async def stream_checkpoint_resume(self, authorization, checkpoint_id, payload):
        self.calls += 1
        data = {"usage": {}} if self.event_name == "runtime.completed" else {"code": "SDK_ERROR"}
        yield f"event: {self.event_name}\ndata: {json.dumps(data)}\n\n".encode()


def test_expired_approval_helper_commits_before_returning_410(monkeypatch) -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(AgentRun.__table__.create)
                await conn.run_sync(AgentApproval.__table__.create)
            async with sessions() as session:
                await SqliteAgentRunRepository(session).create(
                    run_id="run_1",
                    session_id="session_1",
                    user_id="user_1",
                    input_text="approve",
                    status="requires_action",
                )
                await AgentApprovalService(SqliteAgentApprovalRepository(session)).create_for_interruption(
                    run_id="run_1",
                    checkpoint_ref="ckpt_1",
                    user_id="user_1",
                    interruptions=[{"call_id": "call_1", "tool_name": "create_project", "arguments": {}}],
                    expires_at=(datetime.utcnow() - timedelta(seconds=1)).isoformat(),
                )
                await session.commit()

            monkeypatch.setattr(agent_routes, "get_session_maker", lambda: sessions)
            try:
                await agent_routes._claim_approvals_short_tx(
                    run_id="run_1",
                    checkpoint_ref="ckpt_1",
                    user_id="user_1",
                    decision="approve",
                    edited_arguments=None,
                    argument_diff=None,
                    rejection_message=None,
                )
            except AgentApprovalError as exc:
                assert exc.status_code == 410
            else:
                raise AssertionError("Expected expired approval")

            async with sessions() as session:
                rows = await SqliteAgentApprovalRepository(session).list_for_checkpoint(
                    "run_1", "ckpt_1", "user_1"
                )
            assert rows[0]["status"] == "expired"
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_approval_conflict_returns_before_gateway_call(monkeypatch) -> None:
    async def scenario() -> None:
        gateway = CountingGateway()

        async def get_run(*args):
            return {"run_id": "run_1", "checkpoint_ref": "ckpt_1"}

        async def claim(**kwargs):
            raise AgentApprovalError("APPROVAL_CONFLICT", "already claimed", 409)

        monkeypatch.setattr(agent_routes, "_get_run_short_tx", get_run)
        monkeypatch.setattr(agent_routes, "_claim_approvals_short_tx", claim)

        try:
            await agent_routes.resolve_run_approval(
                run_id="run_1",
                checkpoint_id="ckpt_1",
                request=FakeRequest(),
                current_user={"id": "user_1"},
                gateway=gateway,
            )
        except HTTPException as exc:
            assert exc.status_code == 409
            assert exc.detail["error"]["code"] == "APPROVAL_CONFLICT"
        else:
            raise AssertionError("Expected HTTPException")
        assert gateway.calls == 0

    asyncio.run(scenario())


def test_approval_stream_settles_persistent_status(monkeypatch) -> None:
    async def scenario() -> None:
        for event_name, expected in (
            ("runtime.completed", "resolved"),
            ("runtime.error", "failed"),
        ):
            gateway = CountingGateway(event_name)
            approval_statuses = []
            run_status = "requires_action"

            async def get_run(*args):
                return {"run_id": "run_1", "checkpoint_ref": "ckpt_1"}

            async def claim(**kwargs):
                return [{"status": "resuming"}]

            async def mark_approval(**kwargs):
                approval_statuses.append(kwargs["status"])
                return 1

            async def mark_run(run_id, user_id, status, **kwargs):
                nonlocal run_status
                run_status = status
                return {"run_id": run_id, "status": status}

            monkeypatch.setattr(agent_routes, "_get_run_short_tx", get_run)
            monkeypatch.setattr(agent_routes, "_claim_approvals_short_tx", claim)
            monkeypatch.setattr(agent_routes, "_mark_approvals_status_short_tx", mark_approval)
            monkeypatch.setattr(agent_routes, "_mark_run_status_short_tx", mark_run)

            await agent_routes.agent_run_event_bus.create_run("run_1", "session_1", "user_1")
            response = await agent_routes.resolve_run_approval(
                run_id="run_1",
                checkpoint_id="ckpt_1",
                request=FakeRequest(),
                current_user={"id": "user_1"},
                gateway=gateway,
            )
            chunks = []
            async for chunk in response.body_iterator:
                chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)

            assert gateway.calls == 1
            assert approval_statuses == [expected]
            assert run_status == ("completed" if event_name == "runtime.completed" else "error")
            assert event_name in "".join(chunks)

    asyncio.run(scenario())
