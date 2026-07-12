"""Configure the OpenAI Agents SDK tracing backend."""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.core.metrics import AGENT_TRACE_EXPORT_ERRORS

_trace_provider: Any = None


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
