"""Backend Agent product session service."""

from uuid import uuid4

from app.repositories.impl.sqlite_agent_session_repo import SqliteAgentSessionRepository
from app.repositories.impl.sqlite_session_state_repo import SqliteSessionStateRepository


class AgentSessionError(Exception):
    """Product session domain error."""

    def __init__(self, code: str, message: str, status_code: int = 400, retryable: bool = False) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        super().__init__(message)


class AgentSessionService:
    """Coordinates product session metadata and SessionState initialization."""

    def __init__(
        self,
        session_repo: SqliteAgentSessionRepository,
        state_repo: SqliteSessionStateRepository,
    ) -> None:
        self.session_repo = session_repo
        self.state_repo = state_repo

    async def create_session(self, user_id: str, title: str | None = None) -> dict:
        normalized_title = self._normalize_title(title, fallback="新对话")
        session_id = f"session_{uuid4().hex[:16]}"
        item = await self.session_repo.create(session_id=session_id, user_id=user_id, title=normalized_title)
        await self._ensure_state(session_id, user_id)
        return item

    async def list_sessions(
        self,
        user_id: str,
        include_archived: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        return await self.session_repo.list_by_user(
            user_id=user_id,
            include_archived=include_archived,
            limit=max(1, min(limit, 200)),
            offset=max(0, offset),
        )

    async def get_session_detail(self, session_id: str, user_id: str) -> dict:
        item = await self.session_repo.get(session_id, user_id)
        if not item:
            raise AgentSessionError("SESSION_NOT_FOUND", "Session not found", status_code=404)
        state = await self._ensure_state(session_id, user_id)
        return {
            **item,
            "state": self._state_summary(state),
            "messages": [],
        }

    async def rename_session(self, session_id: str, user_id: str, title: str | None) -> dict:
        normalized_title = self._normalize_title(title, fallback="")
        if not normalized_title:
            raise AgentSessionError("SESSION_TITLE_INVALID", "Session title cannot be empty", status_code=422)
        item = await self.session_repo.rename(session_id, user_id, normalized_title)
        if not item:
            await self._raise_missing_or_archived(session_id, user_id)
        return item

    async def archive_session(self, session_id: str, user_id: str) -> dict:
        item = await self.session_repo.archive(session_id, user_id)
        if not item:
            await self._raise_missing_or_archived(session_id, user_id)
        return {"status": "archived", "session_id": session_id}

    async def require_active(self, session_id: str, user_id: str) -> dict:
        item = await self.session_repo.get(session_id, user_id)
        if not item:
            raise AgentSessionError("SESSION_NOT_FOUND", "Session not found", status_code=404)
        if item.get("status") != "active":
            raise AgentSessionError("SESSION_ARCHIVED", "Session is archived", status_code=409)
        await self._ensure_state(session_id, user_id)
        return item

    async def touch(self, session_id: str, user_id: str) -> dict | None:
        return await self.session_repo.touch(session_id, user_id)

    async def _ensure_state(self, session_id: str, user_id: str) -> dict:
        state = await self.state_repo.get(session_id, user_id)
        if state:
            return state
        return await self.state_repo.create(session_id=session_id, user_id=user_id)

    async def _raise_missing_or_archived(self, session_id: str, user_id: str) -> None:
        item = await self.session_repo.get(session_id, user_id)
        if not item:
            raise AgentSessionError("SESSION_NOT_FOUND", "Session not found", status_code=404)
        raise AgentSessionError("SESSION_ARCHIVED", "Session is archived", status_code=409)

    def _normalize_title(self, title: str | None, fallback: str) -> str:
        normalized = str(title or "").strip()[:80]
        return normalized or fallback

    def _state_summary(self, state: dict) -> dict:
        return {
            "mode": state.get("mode", "general"),
            "linked_entities": state.get("linked_entities", {}),
            "summary": state.get("summary", ""),
            "status": state.get("status", "active"),
            "version": state.get("version", 1),
        }
