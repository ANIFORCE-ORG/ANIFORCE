from app.services.agent_run_event_processor import AgentRunEventProcessor


def test_non_terminal_runtime_event_has_no_transition() -> None:
    result = AgentRunEventProcessor().reduce(
        "raw_response_event",
        {"data": {"type": "response.output_text.delta", "delta": "hello"}},
    )

    assert result.transition is None
    assert result.terminal is False


def test_runtime_error_reduces_to_terminal_failure() -> None:
    error = {"code": "UPSTREAM_TIMEOUT", "message": "timeout"}
    result = AgentRunEventProcessor().reduce("runtime.error", error)

    assert result.transition == "error"
    assert result.terminal is True
    assert result.error == error


def test_requires_action_reduces_without_io() -> None:
    result = AgentRunEventProcessor().reduce(
        "runtime.requires_action",
        {"checkpoint_id": "ckpt_1"},
    )

    assert result.transition == "requires_action"
    assert result.terminal is True
    assert result.requires_action is True


def test_completed_and_aborted_have_explicit_transitions() -> None:
    processor = AgentRunEventProcessor()

    completed = processor.reduce("runtime.completed", {"usage": {}})
    aborted = processor.reduce("runtime.aborted", {"message": "cancelled"})

    assert completed.transition == "completed"
    assert completed.terminal is True
    assert aborted.transition == "cancelled"
    assert aborted.terminal is True
