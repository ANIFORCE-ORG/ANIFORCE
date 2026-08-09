"""Project terminal Run status into product Session state."""

from app.repositories.impl.sqlite_session_state_repo import SqliteSessionStateRepository


class SessionSettlementProjection:
    def __init__(self, repository: SqliteSessionStateRepository) -> None:
        self._repository = repository

    async def project(
        self,
        *,
        session_id: str,
        user_id: str,
        run_status: str | None,
        error: dict | None = None,
    ) -> None:
        current = await self._repository.get(session_id, user_id)
        if not current:
            return
        if run_status == "error":
            await self._repository.mark_error(
                session_id,
                user_id,
                current["version"],
                error or {"code": "RUN_FAILED", "message": "Agent run failed", "retryable": True},
            )
        elif run_status in {"completed", "cancelled", "requires_action"}:
            await self._repository.mark_active(session_id, user_id, current["version"])
