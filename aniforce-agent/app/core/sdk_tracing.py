"""Configure the OpenAI Agents SDK tracing backend."""

from __future__ import annotations

import socket
from typing import Any
from urllib.parse import urlparse

from loguru import logger

from app.core.metrics import AGENT_TRACE_EXPORT_ERRORS

_trace_provider: Any = None


def sdk_tracing_status(settings) -> dict[str, Any]:
    """Return tracing configuration and collector reachability for health checks."""
    endpoint = str(settings.PHOENIX_COLLECTOR_ENDPOINT or "")
    parsed = urlparse(endpoint)
    collector_reachable = False
    if parsed.hostname and parsed.port:
        try:
            with socket.create_connection((parsed.hostname, parsed.port), timeout=0.25):
                collector_reachable = True
        except OSError:
            pass
    return {
        "enabled": bool(settings.AGENT_TRACING_ENABLED),
        "provider": str(settings.AGENT_TRACING_PROVIDER or "disabled"),
        "initialized": _trace_provider is not None,
        "collector_endpoint": endpoint,
        "collector_reachable": collector_reachable,
        "project": str(settings.PHOENIX_PROJECT_NAME),
    }


def configure_sdk_tracing(settings) -> Any:
    """Configure SDK tracing without falling back to OpenAI's exporter."""
    global _trace_provider

    from agents import set_tracing_disabled

    provider = str(settings.AGENT_TRACING_PROVIDER or "disabled").strip().lower()
    if not settings.AGENT_TRACING_ENABLED or provider == "disabled":
        set_tracing_disabled(True)
        logger.info("Agents SDK tracing disabled")
        return None

    if provider != "phoenix":
        set_tracing_disabled(True)
        logger.warning("Unsupported Agents SDK tracing provider: {}", provider)
        return None

    status = sdk_tracing_status(settings)
    if not status["collector_reachable"]:
        AGENT_TRACE_EXPORT_ERRORS.labels("collector_unreachable").inc()
        set_tracing_disabled(True)
        logger.error(
            "Phoenix collector is unreachable; SDK tracing disabled: endpoint={}",
            settings.PHOENIX_COLLECTOR_ENDPOINT,
        )
        return None

    try:
        from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
        from phoenix.otel import register

        _trace_provider = register(
            endpoint=settings.PHOENIX_COLLECTOR_ENDPOINT,
            project_name=settings.PHOENIX_PROJECT_NAME,
            protocol="http/protobuf",
            batch=True,
            auto_instrument=False,
            verbose=False,
        )
        OpenAIAgentsInstrumentor().instrument(
            tracer_provider=_trace_provider,
            exclusive_processor=True,
        )
        set_tracing_disabled(False)
        logger.info(
            "Agents SDK tracing enabled: provider=phoenix project={} endpoint={}",
            settings.PHOENIX_PROJECT_NAME,
            settings.PHOENIX_COLLECTOR_ENDPOINT,
        )
        return _trace_provider
    except Exception:
        AGENT_TRACE_EXPORT_ERRORS.labels("initialization").inc()
        set_tracing_disabled(True)
        _trace_provider = None
        logger.exception("Phoenix tracing initialization failed; SDK tracing disabled")
        return None


def shutdown_sdk_tracing() -> None:
    """Flush and stop the configured trace provider."""
    global _trace_provider

    if _trace_provider is None:
        return
    try:
        _trace_provider.force_flush()
        _trace_provider.shutdown()
    except Exception:
        AGENT_TRACE_EXPORT_ERRORS.labels("shutdown").inc()
        logger.exception("Phoenix tracing shutdown failed")
    finally:
        _trace_provider = None
