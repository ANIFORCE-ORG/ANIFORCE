"""Low-cardinality Prometheus metrics for the Agent service."""

from prometheus_client import Counter, Histogram

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
AGENT_RUNS = Counter(
    "aniforce_agent_runs_total",
    "Agent executions by kind and outcome",
    ("execution_kind", "task_type", "outcome"),
)
AGENT_RUN_DURATION = Histogram(
    "aniforce_agent_run_duration_seconds",
    "Agent execution duration",
    ("execution_kind", "task_type"),
)
AGENT_TOKENS = Counter(
    "aniforce_agent_tokens_total",
    "Agent model token usage",
    ("execution_kind", "token_type"),
)
AGENT_TRACE_EXPORT_ERRORS = Counter(
    "aniforce_agent_trace_export_errors_total",
    "Tracing initialization or shutdown failures",
    ("phase",),
)


def observe_tokens(execution_kind: str, usage: dict) -> None:
    values = {
        "input": usage.get("input", usage.get("inputTokens", 0)),
        "output": usage.get("output", usage.get("outputTokens", 0)),
        "cache_read": usage.get("cacheRead", 0),
        "cache_write": usage.get("cacheWrite", 0),
    }
    for token_type, value in values.items():
        if value:
            AGENT_TOKENS.labels(execution_kind, token_type).inc(float(value))
