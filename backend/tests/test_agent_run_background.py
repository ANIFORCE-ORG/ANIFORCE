from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from time import perf_counter

import pytest

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.api.v1 import agent_routes


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


def test_background_unexpected_error_is_redacted(monkeypatch) -> None:
    async def scenario() -> None:
        run_id = "run_failure"
        session_id = "session_failure"
        user_id = "user_1"
        session_state = {"version": 1, "status": "active", "changelog": []}
        persisted_error = None

        async def get_session_state(*args):
            return dict(session_state)

        async def mark_running(*args):
            session_state.update(status="running", version=2)
            return dict(session_state)

        async def mark_error(session_id, user_id, version, error):
            session_state.update(status="error", version=version + 1, last_error=error)
            return dict(session_state)

        async def mark_run_status(run_id, user_id, status, **kwargs):
            nonlocal persisted_error
            persisted_error = kwargs.get("error")
            return {"run_id": run_id, "status": status}

        async def persist_output(**kwargs):
            nonlocal persisted_error
            persisted_error = kwargs.get("error") or persisted_error

        monkeypatch.setattr(agent_routes, "_get_session_state_short_tx", get_session_state)
        monkeypatch.setattr(agent_routes, "_mark_running_short_tx", mark_running)
        monkeypatch.setattr(agent_routes, "_mark_error_short_tx", mark_error)
        monkeypatch.setattr(agent_routes, "_mark_run_status_short_tx", mark_run_status)
        monkeypatch.setattr(agent_routes, "_persist_run_output_short_tx", persist_output)

        await agent_routes.agent_run_event_bus.create_run(run_id, session_id, user_id)
        await agent_routes._consume_agent_run_background(
            run_id=run_id,
            session_id=session_id,
            user_id=user_id,
            authorization="Bearer token",
            agent_payload={},
            changelog_start_index=0,
            gateway=ExplodingGateway(),
            perf_start=perf_counter(),
        )

        public_text = str(persisted_error) + str(session_state.get("last_error"))
        events = agent_routes.agent_run_event_bus._runs[run_id].events
        public_text += "".join(str(event.data) for event in events)
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
    monkeypatch,
    event_name: str,
    data: dict,
    expected_run_status: str,
    expected_session_status: str,
) -> None:
    async def scenario() -> None:
        run_id = f"run_{expected_run_status}"
        session_id = f"session_{expected_run_status}"
        user_id = "user_1"
        session_state = {"version": 1, "status": "active", "changelog": []}
        run_state = {"status": "queued"}

        async def get_session_state(requested_session_id, requested_user_id):
            assert (requested_session_id, requested_user_id) == (session_id, user_id)
            return dict(session_state)

        async def mark_running(requested_session_id, requested_user_id, version):
            assert version == session_state["version"]
            session_state.update(status="running", version=version + 1)
            return dict(session_state)

        async def mark_active(requested_session_id, requested_user_id, version):
            assert version == session_state["version"]
            session_state.update(status="active", version=version + 1)
            return dict(session_state)

        async def mark_error(requested_session_id, requested_user_id, version, error):
            assert version == session_state["version"]
            session_state.update(status="error", version=version + 1, last_error=error)
            return dict(session_state)

        async def mark_run_status(requested_run_id, requested_user_id, status, **kwargs):
            assert (requested_run_id, requested_user_id) == (run_id, user_id)
            if run_state["status"] not in {"completed", "error", "cancelled"}:
                run_state["status"] = status
            return {"run_id": run_id, "status": run_state["status"]}

        async def persist_requires_action(**kwargs):
            assert kwargs == {"run_id": run_id, "user_id": user_id, "data": data}
            return await mark_run_status(run_id, user_id, "requires_action")

        async def persist_output(**kwargs):
            return None

        monkeypatch.setattr(agent_routes, "_get_session_state_short_tx", get_session_state)
        monkeypatch.setattr(agent_routes, "_mark_running_short_tx", mark_running)
        monkeypatch.setattr(agent_routes, "_mark_active_short_tx", mark_active)
        monkeypatch.setattr(agent_routes, "_mark_error_short_tx", mark_error)
        monkeypatch.setattr(agent_routes, "_mark_run_status_short_tx", mark_run_status)
        monkeypatch.setattr(agent_routes, "_persist_requires_action_short_tx", persist_requires_action)
        monkeypatch.setattr(agent_routes, "_persist_run_output_short_tx", persist_output)

        await agent_routes.agent_run_event_bus.create_run(run_id, session_id, user_id)
        await agent_routes._consume_agent_run_background(
            run_id=run_id,
            session_id=session_id,
            user_id=user_id,
            authorization="Bearer token",
            agent_payload={},
            changelog_start_index=0,
            gateway=FakeGateway(event_name, data),
            perf_start=perf_counter(),
        )

        assert run_state["status"] == expected_run_status
        assert session_state["status"] == expected_session_status
        statuses = [
            event.data["status"]
            for event in agent_routes.agent_run_event_bus._runs[run_id].events
            if event.event == "run_status"
        ]
        assert statuses == ["running", expected_run_status]
        assert "completed" not in statuses

    asyncio.run(scenario())
