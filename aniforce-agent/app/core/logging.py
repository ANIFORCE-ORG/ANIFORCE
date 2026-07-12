"""Production-oriented structured logging for the Agent service."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from loguru import logger

from app.core.log_context import enrich_record

TEXT_FORMAT = (
    "<green>{time:YYYY-MM-DDTHH:mm:ss.SSSZ}</green> | "
    "<level>{level: <8}</level> | {extra[service]} | {extra[role]} | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level> | {extra}"
)


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(
    *,
    log_level: str,
    log_file: str | None,
    json_logs: bool,
    console: bool,
    service: str,
    role: str,
    environment: str,
) -> None:
    logger.remove()
    logger.configure(
        patcher=enrich_record,
        extra={
            "service": service,
            "role": role,
            "environment": environment,
            "request_id": None,
            "trace_id": None,
            "span_id": None,
            "run_id": None,
            "session_id": None,
            "worker_id": None,
            "event": None,
        }
    )
    common = {
        "level": log_level.upper(),
        "backtrace": False,
        "diagnose": False,
        "enqueue": True,
    }
    if console:
        logger.add(
            sys.stderr,
            format=TEXT_FORMAT,
            serialize=json_logs,
            colorize=not json_logs and sys.stderr.isatty(),
            **common,
        )
    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            str(path),
            format=TEXT_FORMAT,
            serialize=json_logs,
            colorize=False,
            rotation="100 MB",
            retention="14 days",
            compression="zip",
            **common,
        )

    handler = InterceptHandler()
    logging.basicConfig(handlers=[handler], level=log_level.upper(), force=True)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        target = logging.getLogger(name)
        target.handlers = [handler]
        target.propagate = False
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logger.bind(event="service.logging.configured").info(
        "Logging configured: level={} format={} output={}",
        log_level.upper(),
        "json" if json_logs else "text",
        "both" if console and log_file else "console" if console else "file",
    )


def settings_logging_values(settings) -> dict:
    output = str(settings.LOG_OUTPUT or "console").lower()
    return {
        "log_level": settings.LOG_LEVEL,
        "log_file": settings.LOG_FILE or None,
        "json_logs": str(settings.LOG_FORMAT or "text").lower() == "json",
        "console": output in {"console", "both"},
        "service": settings.LOG_SERVICE,
        "role": settings.LOG_ROLE,
        "environment": settings.APP_ENV,
    }
