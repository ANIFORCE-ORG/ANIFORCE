"""Canonical Agent Run states and transition decisions."""

from __future__ import annotations

from enum import StrEnum


class RunStatus(StrEnum):
    QUEUED = "queued"
    RESUME_QUEUED = "resume_queued"
    RUNNING = "running"
    REQUIRES_ACTION = "requires_action"
    CANCEL_REQUESTED = "cancel_requested"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


ACTIVE_RUN_STATUSES = frozenset(
    {
        RunStatus.QUEUED,
        RunStatus.RESUME_QUEUED,
        RunStatus.RUNNING,
        RunStatus.REQUIRES_ACTION,
        RunStatus.CANCEL_REQUESTED,
    }
)
TERMINAL_RUN_STATUSES = frozenset(
    {RunStatus.COMPLETED, RunStatus.ERROR, RunStatus.CANCELLED, RunStatus.EXPIRED}
)
PERSISTED_TERMINAL_RUN_STATUSES = frozenset(
    {RunStatus.COMPLETED, RunStatus.ERROR, RunStatus.CANCELLED}
)


def is_active(status: str) -> bool:
    return status in ACTIVE_RUN_STATUSES


def is_terminal(status: str) -> bool:
    return status in TERMINAL_RUN_STATUSES


def can_mark_running(status: str) -> bool:
    return not is_terminal(status) and status != RunStatus.RUNNING


def can_finish(status: str) -> bool:
    return not is_terminal(status)


def can_cancel(status: str) -> bool:
    return is_active(status)
