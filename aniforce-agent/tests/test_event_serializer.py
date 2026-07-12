from app.agent.event_serializer import extract_usage, serialize_sdk_event
from app.agent.openai_adapter import OpenAISDKAdapter


def test_sdk_event_serialization_is_json_safe() -> None:
    data = type("Data", (), {"model_dump": lambda self, mode: {"delta": "hello"}})()
    event = type("Event", (), {"type": "raw_response_event", "name": "delta", "data": data})()

    assert serialize_sdk_event(event) == {
        "type": "raw_response_event",
        "class": "Event",
        "name": "delta",
        "data": {"delta": "hello"},
    }


def test_custom_chat_completions_agent_requests_stream_usage() -> None:
    adapter = OpenAISDKAdapter(
        model="test-model",
        api_key="test-key",
        base_url="https://example.invalid/v1",
        enable_tracing=False,
        api_mode="chat_completions",
    )

    agent = adapter.create_agent(name="Test", instructions="Test")

    assert agent.model_settings.include_usage is True


def test_usage_serialization_preserves_cache_tokens() -> None:
    details = type("Details", (), {"cached_tokens": 7})()
    usage = type(
        "Usage",
        (),
        {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15, "input_tokens_details": details},
    )()
    result = type("Result", (), {"context_wrapper": type("Context", (), {"usage": usage})()})()

    assert extract_usage(result) == {
        "input": 10,
        "output": 5,
        "cacheRead": 7,
        "cacheWrite": 0,
        "totalTokens": 15,
    }
