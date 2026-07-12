from __future__ import annotations

import pytest

from app.config.settings import Settings


def test_production_rejects_unsafe_defaults() -> None:
    settings = Settings(
        DEBUG=False,
        JWT_SECRET="change-me-in-production",
        OPENAI_API_KEY="",
    )

    with pytest.raises(ValueError) as caught:
        settings.validate_for_startup()

    message = str(caught.value)
    assert "JWT_SECRET" in message
    assert "OPENAI_API_KEY" in message


def test_sqlite_rejects_multiple_workers(monkeypatch) -> None:
    monkeypatch.setenv("WEB_CONCURRENCY", "2")
    settings = Settings(DEBUG=True, AGENT_RUNTIME_DB_URL="sqlite+aiosqlite:///data/agent.db")

    with pytest.raises(ValueError, match="SQLite runtime storage"):
        settings.validate_for_startup()


def test_debug_single_worker_accepts_local_configuration(monkeypatch) -> None:
    monkeypatch.setenv("WEB_CONCURRENCY", "1")
    Settings(DEBUG=True).validate_for_startup()
