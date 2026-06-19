"""Helpers to mutate Session State after backend business writes."""

from datetime import datetime
from uuid import uuid4

from app.repositories.impl.sqlite_session_state_repo import SessionStateVersionConflict, SqliteSessionStateRepository


async def record_entity_change(
    repo: SqliteSessionStateRepository,
    session_id: str | None,
    user_id: str,
    entity_type: str,
    entity_id: str,
    action: str,
    new_value: dict | None = None,
    run_id: str | None = None,
    tool_call_id: str | None = None,
    linked_entity_updates: dict | None = None,
    field: str | None = None,
    old_value=None,
    rollbackable: bool = False,
) -> dict | None:
    """Append changelog and update linked entity refs for an Agent-triggered write."""
    if not session_id:
        return None

    for _ in range(3):
        state = await repo.get(session_id, user_id)
        if not state:
            return None

        linked_entities = dict(state.get("linked_entities") or {})
        if linked_entity_updates:
            linked_entities.update(linked_entity_updates)

        entry = {
            "id": f"chg_{uuid4().hex}",
            "run_id": run_id,
            "tool_call_id": tool_call_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "field": field,
            "old_value": old_value,
            "new_value": new_value or {},
            "rollbackable": rollbackable,
            "created_at": datetime.utcnow().isoformat(),
        }
        changelog = [*(state.get("changelog") or []), entry]
        try:
            return await repo.update_with_version(
                session_id,
                user_id,
                expected_version=state["version"],
                linked_entities=linked_entities,
                changelog=changelog,
            )
        except SessionStateVersionConflict:
            continue
    raise SessionStateVersionConflict(f"Failed to mutate Session State after retries: {session_id}")
