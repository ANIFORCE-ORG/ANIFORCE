from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agent.api import approvals
from app.agent.approval_commands import AgentApprovalCommands, ResolveApprovalCommand
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


def test_expired_approval_command_commits_before_returning_410() -> None:
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

            try:
                await AgentApprovalCommands(sessions).resolve(
                    ResolveApprovalCommand(
                        run_id="run_1",
                        checkpoint_ref="ckpt_1",
                        user_id="user_1",
                        decision="approve",
                        edited_arguments=None,
                        argument_diff=None,
                        rejection_message=None,
                        resume_payload={},
                    )
                )
            except AgentApprovalError as exc:
                assert exc.status_code == 410
            else:
                raise AssertionError("Expected expired approval")

            async with sessions() as session:
                rows = await SqliteAgentApprovalRepository(session).list_for_checkpoint("run_1", "ckpt_1", "user_1")
            assert rows[0]["status"] == "expired"
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_approval_conflict_returns_before_stream(monkeypatch) -> None:
    async def scenario() -> None:
        async def get_run(*args):
            return {"run_id": "run_1", "session_id": "session_1", "checkpoint_ref": "ckpt_1"}

        async def get_state(*args):
            return {"version": 1, "ui_snapshot": {}}

        async def build_context(*args):
            return "latest context"

        async def resolve(*args):
            raise AgentApprovalError("APPROVAL_CONFLICT", "already claimed", 409)

        monkeypatch.setattr(approvals, "get_run", get_run)
        monkeypatch.setattr(approvals, "get_state", get_state)
        monkeypatch.setattr(approvals, "build_context", build_context)
        monkeypatch.setattr(approvals.AgentApprovalCommands, "resolve", resolve)

        try:
            await approvals.resolve_run_approval(
                run_id="run_1",
                checkpoint_id="ckpt_1",
                request=FakeRequest(),
                current_user={"id": "user_1"},
            )
        except HTTPException as exc:
            assert exc.status_code == 409
            assert exc.detail["error"]["code"] == "APPROVAL_CONFLICT"
        else:
            raise AssertionError("Expected HTTPException")

    asyncio.run(scenario())


def test_approval_api_queues_resume_and_replays_durable_completion(monkeypatch) -> None:
    async def scenario() -> None:
        captured: ResolveApprovalCommand | None = None

        async def get_run(*args):
            return {"run_id": "run_1", "session_id": "session_1", "checkpoint_ref": "ckpt_1", "last_event_sequence": 2}

        async def get_state(*args):
            return {"version": 3, "ui_snapshot": {"route": "/projects"}}

        async def build_context(*args):
            return "latest context"

        async def resolve(_self, command):
            nonlocal captured
            captured = command
            return [{"status": "resuming"}]

        async def list_events(*args):
            return ({"status": "completed"}, [{"sequence": 3, "event_type": "run.completed", "payload": {"run_id": "run_1", "final_output": "done"}}])

        monkeypatch.setattr(approvals, "get_run", get_run)
        monkeypatch.setattr(approvals, "get_state", get_state)
        monkeypatch.setattr(approvals, "build_context", build_context)
        monkeypatch.setattr(approvals.AgentApprovalCommands, "resolve", resolve)
        monkeypatch.setattr(approvals, "list_events", list_events)

        response = await approvals.resolve_run_approval(
            run_id="run_1",
            checkpoint_id="ckpt_1",
            request=FakeRequest(),
            current_user={"id": "user_1"},
        )
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)

        assert captured is not None
        assert captured.resume_payload["context_override"]["business_context_summary"] == "latest context"
        assert "runtime.completed" in "".join(chunks)

    asyncio.run(scenario())
