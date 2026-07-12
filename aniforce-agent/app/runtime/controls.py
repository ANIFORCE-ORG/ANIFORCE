"""Persistent controls shared by Agent Runtime workers."""

from datetime import datetime

from sqlalchemy import text


class RuntimeRunControlStore:
    def __init__(self, engine):
        self.engine = engine

    async def reset(self, run_id: str, user_id: str) -> None:
        now = datetime.utcnow().isoformat()
        async with self.engine.begin() as conn:
            await conn.execute(text(
                "INSERT INTO runtime_run_controls(run_id,user_id,cancel_requested_at,updated_at) "
                "VALUES (:run_id,:user_id,NULL,:now) "
                "ON CONFLICT(run_id) DO UPDATE SET user_id=:user_id,updated_at=:now"
            ), {"run_id": run_id, "user_id": user_id, "now": now})

    async def request_cancel(self, run_id: str, user_id: str) -> bool:
        now = datetime.utcnow().isoformat()
        async with self.engine.begin() as conn:
            result = await conn.execute(text(
                "UPDATE runtime_run_controls SET cancel_requested_at=:now,updated_at=:now "
                "WHERE run_id=:run_id AND user_id=:user_id"
            ), {"run_id": run_id, "user_id": user_id, "now": now})
        return result.rowcount == 1

    async def is_cancel_requested(self, run_id: str, user_id: str) -> bool:
        async with self.engine.connect() as conn:
            result = await conn.execute(text(
                "SELECT cancel_requested_at FROM runtime_run_controls WHERE run_id=:run_id AND user_id=:user_id"
            ), {"run_id": run_id, "user_id": user_id})
            value = result.scalar_one_or_none()
        return value is not None
