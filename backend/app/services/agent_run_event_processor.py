"""Agent run event state machine.

This service keeps route handlers focused on transport concerns. Runtime events are
still the source of truth; the processor applies the backend run state machine and
publishes derived status events.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.services.agent_run_event_bus import AgentRunEventBus

MarkRunStatus = Callable[..., Awaitable[dict | None]]
PersistRequiresAction = Callable[..., Awaitable[dict | None]]


@dataclass(frozen=True)
class AgentRunEventResult:
    terminal: bool = False
    requires_action: bool = False
    persisted_status: str | None = None


class AgentRunEventProcessor:
    def __init__(
        self,
        *,
        event_bus: AgentRunEventBus,
        mark_run_status: MarkRunStatus,
        persist_requires_action: PersistRequiresAction | None = None,
    ) -> None:
        self.event_bus = event_bus
        self.mark_run_status = mark_run_status
        self.persist_requires_action = persist_requires_action

    async def publish_running(self, *, run_id: str, session_id: str | None = None) -> None:
        data: dict[str, Any] = {"run_id": run_id, "status": "running"}
        if session_id:
            data["session_id"] = session_id
        await self.event_bus.publish(run_id, "run_status", data)

    async def handle_runtime_event(
        self,
        *,
        run_id: str,
        user_id: str,
        event_name: str,
        data: dict[str, Any],
        session_id: str | None = None,
        publish_source_event: bool = True,
        complete_immediately: bool = True,
    ) -> AgentRunEventResult:
        if publish_source_event:
            await self.event_bus.publish(run_id, event_name, data)

        if event_name == "runtime.requires_action":
            checkpoint_id = data.get("checkpoint_id") if isinstance(data, dict) else None
            if self.persist_requires_action:
                updated_run = await self.persist_requires_action(
                    run_id=run_id,
                    user_id=user_id,
                    data=data,
                )
            else:
                updated_run = await self.mark_run_status(
                    run_id,
                    user_id,
                    "requires_action",
                    checkpoint_ref=str(checkpoint_id or ""),
                )
            persisted_status = updated_run.get("status") if updated_run else None
            if persisted_status != "requires_action":
                return AgentRunEventResult(
                    terminal=persisted_status in {"completed", "error", "cancelled"},
                    persisted_status=persisted_status,
                )
            status_data: dict[str, Any] = {
                "run_id": run_id,
                "status": "requires_action",
                "checkpoint_ref": checkpoint_id,
            }
            if session_id:
                status_data["session_id"] = session_id
            await self.event_bus.publish(run_id, "run_status", status_data, terminal=True)
            return AgentRunEventResult(terminal=True, requires_action=True, persisted_status=persisted_status)

        if event_name == "runtime.completed":
            if not complete_immediately:
                return AgentRunEventResult()
            return await self.complete_run(run_id=run_id, user_id=user_id, session_id=session_id, usage=data.get("usage") if isinstance(data, dict) else None)

        if event_name == "runtime.error":
            error = data if isinstance(data, dict) else {"message": str(data)}
            updated_run = await self.mark_run_status(run_id, user_id, "error", error=error)
            persisted_status = updated_run.get("status") if updated_run else None
            if persisted_status != "error":
                return AgentRunEventResult(
                    terminal=persisted_status in {"completed", "error", "cancelled"},
                    persisted_status=persisted_status,
                )
            status_data: dict[str, Any] = {"run_id": run_id, "status": "error"}
            if session_id:
                status_data["session_id"] = session_id
            await self.event_bus.publish(run_id, "run_status", status_data, terminal=True)
            return AgentRunEventResult(terminal=True, persisted_status=persisted_status)

        if event_name == "runtime.aborted":
            updated_run = await self.mark_run_status(run_id, user_id, "cancelled")
            persisted_status = updated_run.get("status") if updated_run else None
            if persisted_status != "cancelled":
                return AgentRunEventResult(
                    terminal=persisted_status in {"completed", "error", "cancelled"},
                    persisted_status=persisted_status,
                )
            status_data: dict[str, Any] = {"run_id": run_id, "status": "cancelled"}
            if session_id:
                status_data["session_id"] = session_id
            await self.event_bus.publish(run_id, "run_status", status_data, terminal=True)
            return AgentRunEventResult(terminal=True, persisted_status=persisted_status)

        return AgentRunEventResult()

    async def complete_run(
        self,
        *,
        run_id: str,
        user_id: str,
        session_id: str | None = None,
        usage: dict[str, Any] | None = None,
    ) -> AgentRunEventResult:
        updated_run = await self.mark_run_status(run_id, user_id, "completed", usage=usage)
        persisted_status = updated_run.get("status") if updated_run else None
        if persisted_status != "completed":
            return AgentRunEventResult(
                terminal=persisted_status in {"completed", "error", "cancelled"},
                persisted_status=persisted_status,
            )
        status_data: dict[str, Any] = {"run_id": run_id, "status": "completed"}
        if session_id:
            status_data["session_id"] = session_id
        await self.event_bus.publish(run_id, "run_status", status_data, terminal=True)
        return AgentRunEventResult(terminal=True, persisted_status=persisted_status)
