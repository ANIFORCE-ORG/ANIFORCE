from __future__ import annotations

import asyncio
import sys
from pathlib import Path

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.services.agent_run_event_bus import AgentRunEventBus
from app.services.agent_run_event_processor import AgentRunEventProcessor


def test_complete_does_not_publish_when_persisted_status_is_error() -> None:
    async def scenario() -> None:
        event_bus = AgentRunEventBus()
        await event_bus.create_run("run_1", "session_1", "user_1")

        async def mark_run_status(*args, **kwargs):
            return {"run_id": "run_1", "status": "error"}

        processor = AgentRunEventProcessor(event_bus=event_bus, mark_run_status=mark_run_status)
        result = await processor.complete_run(run_id="run_1", user_id="user_1")

        assert result.terminal is True
        assert result.persisted_status == "error"
        stream = event_bus._runs["run_1"]
        assert stream.events == []
        assert stream.completed is False

    asyncio.run(scenario())


def test_runtime_error_publishes_one_matching_terminal_status() -> None:
    async def scenario() -> None:
        event_bus = AgentRunEventBus()
        await event_bus.create_run("run_1", "session_1", "user_1")
        persisted_status = "running"

        async def mark_run_status(run_id, user_id, status, **kwargs):
            nonlocal persisted_status
            if persisted_status not in {"completed", "error", "cancelled"}:
                persisted_status = status
            return {"run_id": run_id, "status": persisted_status}

        processor = AgentRunEventProcessor(event_bus=event_bus, mark_run_status=mark_run_status)
        error_result = await processor.handle_runtime_event(
            run_id="run_1",
            user_id="user_1",
            session_id="session_1",
            event_name="runtime.error",
            data={"code": "UPSTREAM_TIMEOUT"},
            publish_source_event=False,
        )
        complete_result = await processor.complete_run(run_id="run_1", user_id="user_1")

        assert error_result.persisted_status == "error"
        assert complete_result.persisted_status == "error"
        events = event_bus._runs["run_1"].events
        terminal_statuses = [event.data["status"] for event in events if event.event == "run_status"]
        assert terminal_statuses == ["error"]

    asyncio.run(scenario())


def test_live_subscriber_receives_normalized_error_after_runtime_error() -> None:
    async def scenario() -> None:
        event_bus = AgentRunEventBus()
        await event_bus.create_run("run_1", "session_1", "user_1")

        async def mark_run_status(run_id, user_id, status, **kwargs):
            return {"run_id": run_id, "status": status}

        received = []

        async def subscribe() -> None:
            async for event in event_bus.subscribe("run_1", "user_1"):
                received.append(event)

        subscriber = asyncio.create_task(subscribe())
        await asyncio.sleep(0)
        processor = AgentRunEventProcessor(event_bus=event_bus, mark_run_status=mark_run_status)
        await processor.handle_runtime_event(
            run_id="run_1",
            user_id="user_1",
            event_name="runtime.error",
            data={"code": "UPSTREAM_TIMEOUT"},
        )
        await subscriber

        assert [event.event for event in received] == ["runtime.error", "run_status"]
        assert received[-1].data["status"] == "error"

    asyncio.run(scenario())


def test_requires_action_persists_bound_approval_payload() -> None:
    async def scenario() -> None:
        event_bus = AgentRunEventBus()
        await event_bus.create_run("run_1", "session_1", "user_1")
        captured = None

        async def mark_run_status(*args, **kwargs):
            raise AssertionError("requires_action must use atomic persistence callback")

        async def persist_requires_action(**kwargs):
            nonlocal captured
            captured = kwargs
            return {"run_id": "run_1", "status": "requires_action"}

        data = {
            "checkpoint_id": "ckpt_1",
            "expires_at": "2026-07-11T00:00:00",
            "interruptions": [
                {"call_id": "call_1", "tool_name": "create_project", "arguments": {"name": "demo"}}
            ],
        }
        processor = AgentRunEventProcessor(
            event_bus=event_bus,
            mark_run_status=mark_run_status,
            persist_requires_action=persist_requires_action,
        )
        result = await processor.handle_runtime_event(
            run_id="run_1",
            user_id="user_1",
            event_name="runtime.requires_action",
            data=data,
            publish_source_event=False,
        )

        assert captured == {"run_id": "run_1", "user_id": "user_1", "data": data}
        assert result.requires_action is True
        assert result.persisted_status == "requires_action"

    asyncio.run(scenario())


def test_requires_action_is_not_published_after_terminal_state() -> None:
    async def scenario() -> None:
        event_bus = AgentRunEventBus()
        await event_bus.create_run("run_1", "session_1", "user_1")

        async def mark_run_status(*args, **kwargs):
            return {"run_id": "run_1", "status": "cancelled"}

        processor = AgentRunEventProcessor(event_bus=event_bus, mark_run_status=mark_run_status)
        result = await processor.handle_runtime_event(
            run_id="run_1",
            user_id="user_1",
            event_name="runtime.requires_action",
            data={"checkpoint_id": "ckpt_1"},
            publish_source_event=False,
        )

        assert result.terminal is True
        assert result.requires_action is False
        assert result.persisted_status == "cancelled"
        assert event_bus._runs["run_1"].events == []

    asyncio.run(scenario())
