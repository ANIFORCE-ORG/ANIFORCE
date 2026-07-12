"""Safe structured log enrichment shared by the Agent service."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

SENSITIVE_KEYS = re.compile(
    r"(authorization|cookie|password|passwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token|jwt)",
    re.IGNORECASE,
)
SECRET_VALUE = re.compile(r"(?i)(bearer\s+|sk-)[A-Za-z0-9._~+/-]{8,}")
MAX_DEPTH = 8
MAX_STRING = 4096


def redact(value: Any, *, depth: int = 0) -> Any:
    if depth >= MAX_DEPTH:
        return "[MAX_DEPTH]"
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if SENSITIVE_KEYS.search(str(key)) else redact(item, depth=depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [redact(item, depth=depth + 1) for item in value]
    if isinstance(value, str):
        cleaned = SECRET_VALUE.sub(lambda match: f"{match.group(1)}[REDACTED]", value)
        return cleaned if len(cleaned) <= MAX_STRING else f"{cleaned[:MAX_STRING]}...[TRUNCATED]"
    return value


def enrich_record(record: dict) -> None:
    record["message"] = redact(record.get("message", ""))
    record["extra"] = redact(record.get("extra", {}))
    try:
        from opentelemetry import trace

        context = trace.get_current_span().get_span_context()
        if context.is_valid:
            record["extra"]["trace_id"] = format(context.trace_id, "032x")
            record["extra"]["span_id"] = format(context.span_id, "016x")
    except Exception:
        pass
