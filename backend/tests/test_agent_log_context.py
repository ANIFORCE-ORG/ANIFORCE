from app.config.log_context import enrich_record, redact


def test_redact_removes_nested_secrets_and_truncates() -> None:
    value = {
        "authorization": "Bearer secret-token-value",
        "nested": [{"api_key": "sk-private-value", "safe": "Bearer token-value-123"}],
        "long": "x" * 5000,
    }

    redacted = redact(value)

    assert redacted["authorization"] == "[REDACTED]"
    assert redacted["nested"][0]["api_key"] == "[REDACTED]"
    assert redacted["nested"][0]["safe"] == "Bearer [REDACTED]"
    assert redacted["long"].endswith("...[TRUNCATED]")


def test_enrich_record_redacts_message_and_extra() -> None:
    record = {
        "message": "provider rejected sk-secret-value-123",
        "extra": {"password": "plain-text", "event": "test"},
    }

    enrich_record(record)

    assert "secret-value" not in record["message"]
    assert record["extra"]["password"] == "[REDACTED]"
