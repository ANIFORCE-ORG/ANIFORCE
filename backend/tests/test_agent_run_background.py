from __future__ import annotations

import asyncio
from time import perf_counter

import pytest

from app.agent.execution.executor import execute_agent_run


class ExplodingGateway:
    async def stream_run(self, authorization, payload):
        raise RuntimeError("sk-secret SELECT * FROM users /private/backend.db")
        yield


class FakeGateway:
    def __init__(self, event_name: str, data: dict) -> None:
        self.event_name = event_name
        self.data = data

    async def stream_run(self, authorization, payload):
        import json

        body = json.dumps(self.data, ensure_ascii=False)
        yield f"event: {self.event_name}\ndata: {body}\n\n".encode()


class MemoryExecutionStore:
    def __init__(self, run_id: str, session_id: str, user_id: str) -> None:
        self.run_id = run_id
        self.session_id = session_id
        self.user_id = user_id
        self.session_state = {"version": 1, "status": "active", "changelog": []}
        self.run_state = {"run_id": run_id, "status": "queued"}
        self.persisted_error: dict | None = None
        self.transitions: list[str] = []

    async def get_session_state(self, session_id: str, user_id: str) -> dict:
        assert (session_id, user_id) == (self.session_id, self.user_id)
        return dict(self.session_state)

    async def mark_session_running(self, session_id: str, user_id: str, version: int) -> dict:
        assert version == self.session_state["version"]
        self.session_state.update(status="running", version=version + 1)
        return dict(self.session_state)

    async def settle_session(self, *, session_id, user_id, run_status, error=None) -> None:
        assert (session_id, user_id) == (self.session_id, self.user_id)
        if run_status == "error":
            self.session_state.update(
                status="error",
                version=self.session_state["version"] + 1,
                last_error=error,
            )
        elif run_status in {"completed", "cancelled", "requires_action"}:
            self.session_state.update(status="active", version=self.session_state["version"] + 1)

    async def get_run(self, run_id: str, user_id: str) -> dict:
        return dict(self.run_state)

    async def mark_running(self, run_id: str, user_id: str) -> dict:
        if self.run_state["status"] not in {"completed", "error", "cancelled"}:
            self.run_state["status"] = "running"
            self.transitions.append("running")
        return dict(self.run_state)

    async def complete(self, run_id: str, user_id: str, **kwargs) -> dict:
        self.run_state["status"] = "completed"
        self.transitions.append("completed")
        return dict(self.run_state)

    async def fail(self, run_id: str, user_id: str, error: dict, **kwargs) -> dict:
        if self.run_state["status"] not in {"completed", "error", "cancelled"}:
            self.run_state["status"] = "error"
            self.transitions.append("error")
        self.persisted_error = error
        return dict(self.run_state)

    async def cancel(self, run_id: str, user_id: str, **kwargs) -> dict:
        if self.run_state["status"] not in {"completed", "error", "cancelled"}:
            self.run_state["status"] = "cancelled"
            self.transitions.append("cancelled")
        return dict(self.run_state)

    async def require_action(self, *, run_id: str, user_id: str, data: dict, **kwargs) -> dict:
        self.run_state["status"] = "requires_action"
        self.transitions.append("requires_action")
        return dict(self.run_state)

    async def persist_output(self, **kwargs) -> dict:
        if kwargs.get("error"):
            self.persisted_error = kwargs["error"]
        return dict(self.run_state)


async def run_executor(store: MemoryExecutionStore, gateway) -> list[tuple[str, dict]]:
    published: list[tuple[str, dict]] = []

    class MemoryTransientStream:
        async def publish(self, run_id: str, event: str, data: dict) -> None:
            published.append((event, data))

    await execute_agent_run(
        run_id=store.run_id,
        session_id=store.session_id,
        user_id=store.user_id,
        authorization="Bearer token",
        agent_payload={},
        changelog_start_index=0,
        gateway=gateway,
        perf_start=perf_counter(),
        store=store,
        transient_stream=MemoryTransientStream(),
    )
    return published


def test_background_unexpected_error_is_redacted() -> None:
    async def scenario() -> None:
        store = MemoryExecutionStore("run_failure", "session_failure", "user_1")
        published = await run_executor(store, ExplodingGateway())

        public_text = str(store.persisted_error) + str(store.session_state.get("last_error"))
        public_text += "".join(str(data) for _, data in published)
        assert "RUN_FAILED" in public_text
        assert "sk-secret" not in public_text
        assert "SELECT *" not in public_text
        assert "/private/backend.db" not in public_text

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("event_name", "data", "expected_run_status", "expected_session_status"),
    [
        ("runtime.error", {"code": "UPSTREAM_TIMEOUT", "message": "timeout"}, "error", "error"),
        ("runtime.requires_action", {"checkpoint_id": "ckpt_1"}, "requires_action", "active"),
        ("runtime.aborted", {"message": "cancelled"}, "cancelled", "active"),
    ],
)
def test_background_stream_settles_terminal_state(
    event_name: str,
    data: dict,
    expected_run_status: str,
    expected_session_status: str,
) -> None:
    async def scenario() -> None:
        store = MemoryExecutionStore(
            f"run_{expected_run_status}",
            f"session_{expected_run_status}",
            "user_1",
        )
        published = await run_executor(store, FakeGateway(event_name, data))

        assert store.run_state["status"] == expected_run_status
        assert store.session_state["status"] == expected_session_status
        assert store.transitions == ["running", expected_run_status]
        assert [name for name, _ in published][-1] == event_name
        assert "completed" not in store.transitions

    asyncio.run(scenario())
