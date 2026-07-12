"""Visible Agent message service."""

from app.repositories.impl.sqlite_agent_message_repo import SqliteAgentMessageRepository


class AgentMessageService:
    def __init__(self, repo: SqliteAgentMessageRepository):
        self.repo = repo

    async def append(self, *, session_id: str, user_id: str, role: str, content_json: dict, run_id: str | None = None) -> dict:
        return await self.repo.create(
            session_id=session_id,
            user_id=user_id,
            role=role,
            content_json=content_json,
            run_id=run_id,
        )

    async def list_messages(self, session_id: str, user_id: str) -> list[dict]:
        return await self.repo.list_by_session(session_id, user_id)
