from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

agent_root = Path(__file__).parent.parent
sys.path.insert(0, str(agent_root))

from app.api.runtime_runs import _ACTIVE_RUNTIME_RUNS, run_runtime


class FakeRequest:
    async def json(self) -> dict:
        return {
            "prompt": "hello",
            "session_id": "session_1",
            "run_id": "run_1",
            "user_id": "attacker",
            "auth_token": "attacker-token",
        }


class ExplodingRuntime:
    async def run(self, **kwargs):
        raise RuntimeError("sk-secret SELECT * FROM users /private/runtime.db")
        yield


class FakeRuntime:
    def __init__(self) -> None:
        self.user_id = None
        self.auth_token = None

    async def run(self, **kwargs):
        self.user_id = kwargs["user_id"]
        self.auth_token = kwargs["auth_token"]
        yield {
            "event": "runtime.completed",
            "data": {"final_output": "done"},
            "sequence": 1,
        }


def test_unexpected_runtime_error_is_redacted_from_stream() -> None:
    async def scenario() -> None:
        response = await run_runtime(
            request=FakeRequest(),
            user={"id": "authenticated_user"},
            runtime=ExplodingRuntime(),
        )
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
        body = "".join(chunks)

        assert "INTERNAL_SERVER_ERROR" in body
        assert "Agent service failed unexpectedly" in body
        assert "sk-secret" not in body
        assert "SELECT *" not in body
        assert "/private/runtime.db" not in body

    asyncio.run(scenario())


def test_runtime_uses_authenticated_identity_not_body_user_id() -> None:
    async def scenario() -> None:
        runtime = FakeRuntime()
        response = await run_runtime(
            request=FakeRequest(),
            user={"id": "authenticated_user", "token": "trusted-token"},
            runtime=runtime,
        )
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)

        assert runtime.user_id == "authenticated_user"
        assert runtime.auth_token == "trusted-token"
        assert "attacker" not in "".join(chunks)
        assert "run_1" not in _ACTIVE_RUNTIME_RUNS

    asyncio.run(scenario())
