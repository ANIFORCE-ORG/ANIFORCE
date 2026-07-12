from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from fastapi import HTTPException

agent_root = Path(__file__).parent.parent
sys.path.insert(0, str(agent_root))

from app.runtime.sessions import RuntimeSessionNotRegistered, RuntimeSessionOwnerMismatch
from app.api.runtime_checkpoints import resume_checkpoint
from app.api.runtime_sessions import get_session_history


class FakeResumeRequest:
    async def json(self) -> dict:
        return {"decision": "approve", "auth_token": "attacker-token"}


class ExplodingRuntime:
    def __init__(self) -> None:
        self.auth_token = None

    async def claim_checkpoint_for_resume(self, **kwargs):
        return {"id": kwargs["checkpoint_id"], "status": "resuming"}

    async def resume_checkpoint(self, **kwargs):
        self.auth_token = kwargs["auth_token"]
        raise RuntimeError("sk-secret SELECT * FROM checkpoints /private/agent.db")
        yield

    async def get_session_history(self, session_id: str, user_id: str):
        raise RuntimeError("sk-secret SELECT * FROM sessions /private/agent.db")


class ClaimBoundaryRuntime:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def claim_checkpoint_for_resume(self, **kwargs):
        raise self.error


class HistoryBoundaryRuntime:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def get_session_history(self, session_id: str, user_id: str):
        raise self.error


def test_checkpoint_api_returns_claim_http_status() -> None:
    from app.runtime.checkpoints.store import RuntimeCheckpointClaimError

    async def scenario() -> None:
        for status_code, code in ((410, "CHECKPOINT_EXPIRED"), (409, "CHECKPOINT_CONFLICT")):
            try:
                await resume_checkpoint(
                    checkpoint_id="ckpt_1",
                    request=FakeResumeRequest(),
                    user={"id": "user_1", "token": "trusted-token", "token_type": "agent_worker", "worker_id": "worker_1"},
                    runtime=ClaimBoundaryRuntime(
                        RuntimeCheckpointClaimError(code, "Checkpoint unavailable", status_code)
                    ),
                )
            except HTTPException as exc:
                assert exc.status_code == status_code
                assert exc.detail["code"] == code
            else:
                raise AssertionError("Expected HTTPException")

    asyncio.run(scenario())


def test_checkpoint_api_redacts_unexpected_error() -> None:
    async def scenario() -> None:
        runtime = ExplodingRuntime()
        response = await resume_checkpoint(
            checkpoint_id="ckpt_1",
            request=FakeResumeRequest(),
            user={"id": "user_1", "token": "trusted-token", "token_type": "agent_worker", "worker_id": "worker_1"},
            runtime=runtime,
        )
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
        body = "".join(chunks)

        assert runtime.auth_token == "trusted-token"
        assert "INTERNAL_SERVER_ERROR" in body
        assert "Agent service failed unexpectedly" in body
        assert "sk-secret" not in body
        assert "SELECT *" not in body
        assert "/private/agent.db" not in body

    asyncio.run(scenario())


def test_history_api_rejects_cross_user_access() -> None:
    async def scenario() -> None:
        try:
            await get_session_history(
                session_id="session_1",
                user={"id": "attacker"},
                runtime=HistoryBoundaryRuntime(RuntimeSessionOwnerMismatch("session_1")),
            )
        except HTTPException as exc:
            assert exc.status_code == 403
            assert exc.detail["code"] == "SESSION_FORBIDDEN"
        else:
            raise AssertionError("Expected HTTPException")

    asyncio.run(scenario())


def test_history_api_rejects_unregistered_session() -> None:
    async def scenario() -> None:
        try:
            await get_session_history(
                session_id="session_1",
                user={"id": "user_1"},
                runtime=HistoryBoundaryRuntime(RuntimeSessionNotRegistered("session_1")),
            )
        except HTTPException as exc:
            assert exc.status_code == 404
            assert exc.detail["code"] == "SESSION_NOT_FOUND"
        else:
            raise AssertionError("Expected HTTPException")

    asyncio.run(scenario())


def test_history_api_redacts_unexpected_error() -> None:
    async def scenario() -> None:
        try:
            await get_session_history(
                session_id="session_1",
                user={"id": "user_1"},
                runtime=ExplodingRuntime(),
            )
        except HTTPException as exc:
            assert exc.status_code == 500
            detail = str(exc.detail)
            assert "HISTORY_ERROR" in detail
            assert "Session history is temporarily unavailable" in detail
            assert "sk-secret" not in detail
            assert "SELECT *" not in detail
            assert "/private/agent.db" not in detail
        else:
            raise AssertionError("Expected HTTPException")

    asyncio.run(scenario())
