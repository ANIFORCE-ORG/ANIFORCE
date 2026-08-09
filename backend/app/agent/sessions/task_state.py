"""Validation and persistence rules for cross-run Agent task memory."""

from __future__ import annotations

from typing import Any

from app.repositories.impl.sqlite_session_state_repo import (
    SessionStateVersionConflict,
    SqliteSessionStateRepository,
)


ACTIVE_SKILL_STATUSES = frozenset({"selected", "collecting_inputs", "ready", "executing"})
ALL_SKILL_STATUSES = ACTIVE_SKILL_STATUSES | {"completed", "cancelled", "failed"}


def normalize_task_state(value: Any) -> dict:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    active = value.get("active_skill")
    if isinstance(active, dict):
        name = str(active.get("name") or "")[:80]
        version = str(active.get("version") or "")[:32]
        status = str(active.get("status") or "selected")
        if name and version and status in ALL_SKILL_STATUSES:
            slots = active.get("slots") if isinstance(active.get("slots"), dict) else {}
            missing = active.get("missing_slots") if isinstance(active.get("missing_slots"), list) else []
            result["active_skill"] = {
                "name": name,
                "version": version,
                "status": status,
                "slots": {str(key)[:80]: item for key, item in list(slots.items())[:30]},
                "missing_slots": [str(item)[:80] for item in missing[:20]],
                "load_reason": str(active.get("load_reason") or "")[:80] or None,
                "pending_question": str(active.get("pending_question") or "")[:500] or None,
            }
    confirmed = value.get("confirmed_entities")
    if isinstance(confirmed, dict):
        result["confirmed_entities"] = {
            str(key)[:40]: str(item)[:128]
            for key, item in list(confirmed.items())[:20]
            if item
        }
    constraints = value.get("constraints")
    if isinstance(constraints, dict):
        result["constraints"] = dict(list(constraints.items())[:30])
    if value.get("last_conclusion"):
        result["last_conclusion"] = str(value["last_conclusion"])[:1000]
    return result


async def persist_task_state(
    repository: SqliteSessionStateRepository,
    session_id: str,
    user_id: str,
    task_state: dict,
) -> dict | None:
    normalized = normalize_task_state(task_state)
    for _ in range(3):
        current = await repository.get(session_id, user_id)
        if current is None:
            return None
        try:
            return await repository.update_task_state(
                session_id,
                user_id,
                current["version"],
                normalized,
            )
        except SessionStateVersionConflict:
            continue
    raise SessionStateVersionConflict(f"Could not persist task state for session {session_id}")
