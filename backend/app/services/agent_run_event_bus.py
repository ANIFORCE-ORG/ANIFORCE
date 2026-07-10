"""In-memory run event log and subscriber bus for Agent runs."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, AsyncIterator


@dataclass
class RunEvent:
    sequence: int
    event: str
    data: dict[str, Any]
    created_at: str


@dataclass
class RunEventStream:
    run_id: str
    session_id: str
    user_id: str
    events: list[RunEvent] = field(default_factory=list)
    subscribers: list[asyncio.Queue[RunEvent]] = field(default_factory=list)
    completed: bool = False
    terminal_event: str | None = None
    updated_at: datetime = field(default_factory=datetime.utcnow)


class AgentRunEventBus:
    def __init__(self) -> None:
        self._runs: dict[str, RunEventStream] = {}
        self._guard = asyncio.Lock()
        self._ttl = timedelta(hours=2)

    async def create_run(self, run_id: str, session_id: str, user_id: str) -> None:
        async with self._guard:
            self._gc_locked()
            self._runs[run_id] = RunEventStream(run_id=run_id, session_id=session_id, user_id=user_id)

    async def publish(self, run_id: str, event: str, data: dict[str, Any], terminal: bool = False) -> RunEvent:
        async with self._guard:
            stream = self._runs.get(run_id)
            if not stream:
                raise KeyError(f"Run not found: {run_id}")
            item = RunEvent(
                sequence=len(stream.events) + 1,
                event=event,
                data=data,
                created_at=datetime.utcnow().isoformat(),
            )
            stream.events.append(item)
            stream.updated_at = datetime.utcnow()
            if terminal:
                stream.completed = True
                stream.terminal_event = event
            subscribers = list(stream.subscribers)
        for queue in subscribers:
            try:
                queue.put_nowait(item)
            except asyncio.QueueFull:
                pass
        return item

    async def subscribe(self, run_id: str, user_id: str, after_sequence: int = 0) -> AsyncIterator[RunEvent]:
        queue: asyncio.Queue[RunEvent] = asyncio.Queue(maxsize=1000)
        async with self._guard:
            stream = self._runs.get(run_id)
            if not stream or stream.user_id != user_id:
                raise KeyError(f"Run not found: {run_id}")
            history = [event for event in stream.events if event.sequence > after_sequence]
            completed = stream.completed
            if not completed:
                stream.subscribers.append(queue)
        try:
            for event in history:
                yield event
            if completed:
                return
            while True:
                event = await queue.get()
                yield event
                if event.event in {"run_status", "error"}:
                    status = event.data.get("status") if isinstance(event.data, dict) else None
                    if status in {"completed", "error", "failed", "cancelled", "requires_action"} or event.event == "error":
                        return
        finally:
            async with self._guard:
                stream = self._runs.get(run_id)
                if stream and queue in stream.subscribers:
                    stream.subscribers.remove(queue)

    def _gc_locked(self) -> None:
        now = datetime.utcnow()
        expired = [run_id for run_id, stream in self._runs.items() if now - stream.updated_at > self._ttl]
        for run_id in expired:
            self._runs.pop(run_id, None)


agent_run_event_bus = AgentRunEventBus()
