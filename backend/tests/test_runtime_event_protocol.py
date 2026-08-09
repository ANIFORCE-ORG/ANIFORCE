from app.agent.execution.protocol import is_client_stream_event, parse_sse_events


def test_parse_sse_events_preserves_incomplete_frame() -> None:
    events, remainder = parse_sse_events(
        'event: raw_response_event\ndata: {"data":{"type":"response.output_text.delta"}}\n\n'
        'event: runtime.completed\ndata: {"status":"complete"}'
    )
    assert events == [("raw_response_event", {"data": {"type": "response.output_text.delta"}})]
    assert remainder == 'event: runtime.completed\ndata: {"status":"complete"}'


def test_parse_sse_events_keeps_existing_non_object_contract() -> None:
    events, remainder = parse_sse_events("event: message\ndata: [1, 2]\n\n")
    assert events == [("message", {"value": [1, 2]})]
    assert remainder == ""


def test_client_stream_filter_exposes_only_incremental_events() -> None:
    assert is_client_stream_event("raw_response_event", {"data": {"type": "response.reasoning_text.delta"}})
    assert is_client_stream_event("run_item_stream_event", {"name": "tool_called"})
    assert is_client_stream_event("agent_updated_stream_event", {})
    assert not is_client_stream_event("runtime.completed", {"status": "completed"})
