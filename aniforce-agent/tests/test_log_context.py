from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from app.core.log_context import enrich_record, redact


def test_redact_removes_nested_secrets() -> None:
    redacted = redact(
        {
            "access_token": "token-value",
            "items": [{"client_secret": "secret", "text": "Bearer token-value-123"}],
        }
    )

    assert redacted["access_token"] == "[REDACTED]"
    assert redacted["items"][0]["client_secret"] == "[REDACTED]"
    assert redacted["items"][0]["text"] == "Bearer [REDACTED]"


def test_enrich_record_adds_active_trace_context() -> None:
    provider = TracerProvider()
    tracer = provider.get_tracer(__name__)
    record = {"message": "safe", "extra": {"trace_id": None, "span_id": None}}

    with tracer.start_as_current_span("test") as span:
        enrich_record(record)
        context = span.get_span_context()

    assert record["extra"]["trace_id"] == format(context.trace_id, "032x")
    assert record["extra"]["span_id"] == format(context.span_id, "016x")
