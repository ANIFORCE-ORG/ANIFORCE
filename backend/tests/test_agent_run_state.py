import pytest

from app.agent.run_state import (
    RunStatus,
    can_cancel,
    can_finish,
    can_mark_running,
    is_active,
    is_terminal,
)


@pytest.mark.parametrize(
    ("status", "active", "terminal"),
    [
        (RunStatus.QUEUED, True, False),
        (RunStatus.RESUME_QUEUED, True, False),
        (RunStatus.RUNNING, True, False),
        (RunStatus.REQUIRES_ACTION, True, False),
        (RunStatus.CANCEL_REQUESTED, True, False),
        (RunStatus.COMPLETED, False, True),
        (RunStatus.ERROR, False, True),
        (RunStatus.CANCELLED, False, True),
        (RunStatus.EXPIRED, False, True),
    ],
)
def test_run_status_classification(status: RunStatus, active: bool, terminal: bool) -> None:
    assert is_active(status) is active
    assert is_terminal(status) is terminal


def test_transition_decisions_preserve_current_service_behavior() -> None:
    assert can_mark_running(RunStatus.QUEUED)
    assert can_mark_running(RunStatus.RESUME_QUEUED)
    assert can_mark_running(RunStatus.REQUIRES_ACTION)
    assert not can_mark_running(RunStatus.RUNNING)
    assert can_finish(RunStatus.RUNNING)
    assert not can_finish(RunStatus.COMPLETED)
    assert can_cancel(RunStatus.CANCEL_REQUESTED)
    assert not can_cancel(RunStatus.COMPLETED)
