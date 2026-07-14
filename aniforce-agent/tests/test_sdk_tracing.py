from types import SimpleNamespace

from app.core import sdk_tracing


class _Connection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


def settings(endpoint="http://127.0.0.1:6006/v1/traces"):
    return SimpleNamespace(
        AGENT_TRACING_ENABLED=True,
        AGENT_TRACING_PROVIDER="phoenix",
        PHOENIX_COLLECTOR_ENDPOINT=endpoint,
        PHOENIX_PROJECT_NAME="aniforce",
    )


def test_sdk_tracing_status_reports_reachable_collector(monkeypatch):
    monkeypatch.setattr(sdk_tracing.socket, "create_connection", lambda address, timeout: _Connection())

    status = sdk_tracing.sdk_tracing_status(settings())

    assert status == {
        "enabled": True,
        "provider": "phoenix",
        "initialized": False,
        "collector_endpoint": "http://127.0.0.1:6006/v1/traces",
        "collector_reachable": True,
        "project": "aniforce",
    }


def test_sdk_tracing_status_rejects_endpoint_without_port():
    status = sdk_tracing.sdk_tracing_status(settings("http://localhost/v1/traces"))

    assert status["collector_reachable"] is False
