"""Session State Repository SQLite implementation."""

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SessionState


class SessionStateVersionConflict(Exception):
    """Raised when optimistic locking detects a stale session state version."""


class SqliteSessionStateRepository:
    """Data access for minimal Agent Session State."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _loads(self, value: str | None, default: Any) -> Any:
        if not value:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default

    def _to_dict(self, state: SessionState) -> dict:
        return {
            "session_id": state.session_id,
            "user_id": state.user_id,
            "mode": state.mode,
            "linked_entities": self._loads(state.linked_entities_json, {}),
            "summary": state.summary,
            "pending_actions": self._loads(state.pending_actions_json, []),
            "changelog": self._loads(state.changelog_json, []),
            "ui_snapshot": self._loads(state.ui_snapshot_json, None),
            "task_state": self._loads(state.task_state_json, {}),
            "version": state.version,
            "status": state.status,
            "last_error": self._loads(state.last_error_json, None),
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat(),
        }

    async def create(self, session_id: str, user_id: str, mode: str = "general") -> dict:
        state = SessionState(session_id=session_id, user_id=user_id, mode=mode)
        self.session.add(state)
        await self.session.flush()
        return self._to_dict(state)

    async def get(self, session_id: str, user_id: str) -> dict | None:
        result = await self.session.execute(
            select(SessionState).where(
                SessionState.session_id == session_id,
                SessionState.user_id == user_id,
            )
        )
        state = result.scalar_one_or_none()
        return self._to_dict(state) if state else None

    async def get_by_session_id(self, session_id: str) -> dict | None:
        result = await self.session.execute(
            select(SessionState).where(SessionState.session_id == session_id)
        )
        state = result.scalar_one_or_none()
        return self._to_dict(state) if state else None

    async def update_with_version(
        self,
        session_id: str,
        user_id: str,
        expected_version: int,
        **kwargs: Any,
    ) -> dict:
        values = self._serialize_update_values(kwargs)
        values["version"] = expected_version + 1
        values["updated_at"] = datetime.utcnow()

        result = await self.session.execute(
            update(SessionState)
            .where(
                SessionState.session_id == session_id,
                SessionState.user_id == user_id,
                SessionState.version == expected_version,
            )
            .values(**values)
        )
        if result.rowcount != 1:
            raise SessionStateVersionConflict(
                f"SessionState version conflict: session_id={session_id}, expected={expected_version}"
            )
        await self.session.flush()
        updated_state = await self.get(session_id, user_id)
        if updated_state is None:
            raise ValueError(f"SessionState {session_id} not found after update")
        return updated_state

    async def update_linked_entities(
        self,
        session_id: str,
        user_id: str,
        expected_version: int,
        linked_entities: dict,
    ) -> dict:
        return await self.update_with_version(
            session_id,
            user_id,
            expected_version,
            linked_entities=linked_entities,
        )

    async def update_ui_snapshot(
        self,
        session_id: str,
        user_id: str,
        expected_version: int,
        ui_snapshot: dict | None,
    ) -> dict:
        return await self.update_with_version(
            session_id,
            user_id,
            expected_version,
            ui_snapshot=ui_snapshot,
        )

    async def update_task_state(
        self,
        session_id: str,
        user_id: str,
        expected_version: int,
        task_state: dict,
    ) -> dict:
        return await self.update_with_version(
            session_id,
            user_id,
            expected_version,
            task_state=task_state,
        )

    async def append_changelog(
        self,
        session_id: str,
        user_id: str,
        expected_version: int,
        entry: dict,
    ) -> dict:
        state = await self.get(session_id, user_id)
        if state is None:
            raise ValueError(f"SessionState {session_id} not found")
        changelog = [*state["changelog"], entry]
        return await self.update_with_version(
            session_id,
            user_id,
            expected_version,
            changelog=changelog,
        )

    async def mark_running(self, session_id: str, user_id: str, expected_version: int) -> dict:
        return await self.update_with_version(
            session_id,
            user_id,
            expected_version,
            status="running",
            last_error=None,
        )

    async def mark_active(self, session_id: str, user_id: str, expected_version: int) -> dict:
        return await self.update_with_version(
            session_id,
            user_id,
            expected_version,
            status="active",
            last_error=None,
        )

    async def mark_error(
        self,
        session_id: str,
        user_id: str,
        expected_version: int,
        error: dict,
    ) -> dict:
        return await self.update_with_version(
            session_id,
            user_id,
            expected_version,
            status="error",
            last_error=error,
        )

    def _serialize_update_values(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        values: dict[str, Any] = {}
        json_field_map = {
            "linked_entities": "linked_entities_json",
            "pending_actions": "pending_actions_json",
            "changelog": "changelog_json",
            "ui_snapshot": "ui_snapshot_json",
            "task_state": "task_state_json",
            "last_error": "last_error_json",
        }
        for key, value in kwargs.items():
            if key in json_field_map:
                values[json_field_map[key]] = json.dumps(value, ensure_ascii=False) if value is not None else None
            elif key in {"mode", "summary", "status"}:
                values[key] = value
            else:
                raise ValueError(f"Unsupported SessionState update field: {key}")
        return values
