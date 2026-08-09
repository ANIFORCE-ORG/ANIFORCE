"""Uniform read-after-write verification for MCP business mutations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.backend_client import BackendResponseError, BackendUnavailableError


Fetch = Callable[[], Awaitable[dict]]


def _same(actual: Any, expected: Any) -> bool:
    if isinstance(expected, float) and isinstance(actual, (int, float)):
        return abs(float(actual) - expected) < 1e-9
    if isinstance(expected, list) and isinstance(actual, list):
        return sorted(map(str, actual)) == sorted(map(str, expected))
    if isinstance(expected, str) and isinstance(actual, str):
        if len(actual) == 10 and len(expected) > 10 and expected.startswith(actual):
            return True
        if len(expected) == 10 and len(actual) > 10 and actual.startswith(expected):
            return True
    return actual == expected


def _attach(result: dict, *, status: str, operation_status: str, **details: Any) -> dict:
    return {
        **result,
        "operation_status": operation_status,
        "verification": {"status": status, **details},
    }


async def verify_fields(
    result: dict,
    fetch: Fetch,
    expected: dict[str, Any],
    *,
    entity_id: str,
) -> dict:
    try:
        actual = await fetch()
    except BackendUnavailableError:
        return _attach(
            result,
            status="unknown",
            operation_status="status_unknown",
            entity_id=entity_id,
            message="Write returned success, but read-after-write verification was unavailable.",
        )
    except BackendResponseError as exc:
        return _attach(
            result,
            status="failed",
            operation_status="executed_verification_failed",
            entity_id=entity_id,
            error_code=exc.code,
        )
    mismatches = {
        field: {"expected": value, "actual": actual.get(field)}
        for field, value in expected.items()
        if not _same(actual.get(field), value)
    }
    if mismatches:
        return _attach(
            result,
            status="failed",
            operation_status="executed_verification_failed",
            entity_id=entity_id,
            mismatches=mismatches,
        )
    return _attach(
        result,
        status="passed",
        operation_status="executed_and_verified",
        entity_id=entity_id,
        checked_fields=sorted(expected),
    )


async def verify_absent(result: dict, fetch: Fetch, *, entity_id: str) -> dict:
    try:
        await fetch()
    except BackendResponseError as exc:
        if exc.status == 404:
            return _attach(
                result,
                status="passed",
                operation_status="executed_and_verified",
                entity_id=entity_id,
                checked="not_found",
            )
        return _attach(
            result,
            status="failed",
            operation_status="executed_verification_failed",
            entity_id=entity_id,
            error_code=exc.code,
        )
    except BackendUnavailableError:
        return _attach(
            result,
            status="unknown",
            operation_status="status_unknown",
            entity_id=entity_id,
            message="Delete returned success, but absence could not be verified.",
        )
    return _attach(
        result,
        status="failed",
        operation_status="executed_verification_failed",
        entity_id=entity_id,
        message="Entity still exists after delete returned success.",
    )


async def verify_collection_membership(
    result: dict,
    fetch: Fetch,
    *,
    collection_key: str,
    entity_id: str,
    should_exist: bool,
) -> dict:
    try:
        payload = await fetch()
    except BackendUnavailableError:
        return _attach(
            result,
            status="unknown",
            operation_status="status_unknown",
            entity_id=entity_id,
            message="Association write returned success, but verification was unavailable.",
        )
    except BackendResponseError as exc:
        return _attach(
            result,
            status="failed",
            operation_status="executed_verification_failed",
            entity_id=entity_id,
            error_code=exc.code,
        )
    items = payload.get(collection_key) or []
    ids = {
        str(item.get("id") if isinstance(item, dict) else item)
        for item in items
    }
    passed = (entity_id in ids) is should_exist
    return _attach(
        result,
        status="passed" if passed else "failed",
        operation_status="executed_and_verified" if passed else "executed_verification_failed",
        entity_id=entity_id,
        checked=f"membership:{collection_key}",
        expected_present=should_exist,
    )
