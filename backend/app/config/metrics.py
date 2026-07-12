"""Low-cardinality Prometheus metrics with startup-safe degradation."""

from __future__ import annotations

from typing import Any

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

    METRICS_AVAILABLE = True
except ImportError:
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"
    METRICS_AVAILABLE = False

    class _NoopMetric:
        def labels(self, *args: Any, **kwargs: Any) -> "_NoopMetric":
            return self

        def inc(self, amount: float = 1) -> None:
            return None

        def dec(self, amount: float = 1) -> None:
            return None

        def observe(self, amount: float) -> None:
            return None

    def Counter(*args: Any, **kwargs: Any) -> _NoopMetric:  # type: ignore[misc]
        return _NoopMetric()

    def Gauge(*args: Any, **kwargs: Any) -> _NoopMetric:  # type: ignore[misc]
        return _NoopMetric()

    def Histogram(*args: Any, **kwargs: Any) -> _NoopMetric:  # type: ignore[misc]
        return _NoopMetric()

    def generate_latest() -> bytes:
        return b""


HTTP_REQUESTS = Counter(
    "aniforce_http_requests_total",
    "HTTP requests completed",
    ("service", "method", "route", "status_class"),
)
HTTP_DURATION = Histogram(
    "aniforce_http_request_duration_seconds",
    "HTTP request duration",
    ("service", "method", "route"),
)
AGENT_RUN_WORKER_EXECUTIONS = Counter(
    "aniforce_agent_worker_executions_total",
    "Agent runs claimed by Backend workers",
    ("execution_kind", "outcome"),
)
AGENT_RUN_WORKER_DURATION = Histogram(
    "aniforce_agent_worker_execution_duration_seconds",
    "Backend Agent worker execution duration",
    ("execution_kind",),
)
AGENT_RUN_WORKER_ACTIVE = Gauge(
    "aniforce_agent_worker_active_runs",
    "Agent runs currently owned by this worker process",
)
AGENT_WORKER_ERRORS = Counter(
    "aniforce_agent_worker_errors_total",
    "Agent worker iteration and lease errors",
    ("kind",),
)
AGENT_RECONCILE_RUNS = Counter(
    "aniforce_agent_reconcile_runs_total",
    "Reconciliation iterations",
    ("outcome",),
)
AGENT_RECONCILE_ACTIONS = Counter(
    "aniforce_agent_reconcile_actions_total",
    "Reconciliation actions and conflicts",
    ("kind",),
)
