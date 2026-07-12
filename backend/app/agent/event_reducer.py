"""Reduce Runtime events into run execution outcomes without performing IO."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentRunEventResult:
    transition: str | None = None
    terminal: bool = False
    requires_action: bool = False
    error: dict[str, Any] | None = None


class AgentRunEventProcessor:
    """Classify Runtime protocol events for the run executor."""

    def reduce(self, event_name: str, data: dict[str, Any]) -> AgentRunEventResult:
        if event_name == "runtime.requires_action":
            return AgentRunEventResult(
                transition="requires_action",
                terminal=True,
                requires_action=True,
            )
        if event_name == "runtime.completed":
            return AgentRunEventResult(transition="completed", terminal=True)
        if event_name == "runtime.error":
            return AgentRunEventResult(
                transition="error",
                terminal=True,
                error=data if isinstance(data, dict) else {"message": str(data)},
            )
        if event_name == "runtime.aborted":
            return AgentRunEventResult(transition="cancelled", terminal=True)
        return AgentRunEventResult()
