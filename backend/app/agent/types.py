"""Typed internal contracts shared across Backend Agent domains."""

from typing import Any, TypedDict


class RunExecutionContext(TypedDict):
    task_type: str
    business_context_summary: str
    ui_snapshot: dict[str, Any]
    session_state: dict[str, Any]
    changelog_start_index: int


class RuntimeEvent(TypedDict):
    event: str
    data: dict[str, Any]
    sequence: int
