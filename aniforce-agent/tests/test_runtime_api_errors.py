from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from fastapi import HTTPException

agent_root = Path(__file__).parent.parent
sys.path.insert(0, str(agent_root))

from app.api.runtime_checkpoints import resume_checkpoint
from app.api.runtime_sessions import get_session_history


class FakeResumeRequest:
    async def json(self) -> dict:
        return {"decision": "approve", "auth_token": "attacker-token"}


class ExplodingRuntime:
    def __init__(self) -> None:
        self.auth_token = None

    async def resume_checkpoint(self, **kwargs):
        self.auth_token = kwargs["auth_token"]
        raise RuntimeError("sk-secret SELECT * FROM checkpoints /private/agent.db")
        yield

    async def get_session_history(self, session_id: str):
        raise RuntimeError("sk-secret SELECT * FROM sessions /private/agent.db")


def test_checkpoint_api_redacts_unexpected_error() -> None:
    async def scenario() -> None:
        runtime = ExplodingRuntime()
        response = await resume_checkpoint(
            checkpoint_id="ckpt_1",
            request=FakeResumeRequest(),
            user={"id": "user_1", "token": "trusted-token"},
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
