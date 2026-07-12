"""Shared HTTP and short-transaction helpers for Agent transport routes."""

import json
from collections.abc import Awaitable, Callable
from typing import TypeVar

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_session_maker

T = TypeVar("T")


def authorization(request: Request) -> str | None:
    value = request.headers.get("Authorization")
    return value if value else None


def error_payload(
    code: str,
    message: str,
    retryable: bool = False,
    details: dict | None = None,
) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "retryable": retryable,
            "details": details or {},
        }
    }


def sse_event(event: str, data: dict, event_id: str | int | None = None) -> bytes:
    parts = []
    if event_id is not None:
        parts.append(f"id: {event_id}")
    parts.append(f"event: {event}")
    parts.append(f"data: {json.dumps(data, ensure_ascii=False, default=str)}")
    return ("\n".join(parts) + "\n\n").encode("utf-8")


async def with_session(operation: Callable[[AsyncSession], Awaitable[T]]) -> T:
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            result = await operation(session)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise
