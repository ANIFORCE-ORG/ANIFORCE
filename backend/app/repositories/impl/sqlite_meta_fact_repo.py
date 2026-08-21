"""SQLite persistence for the single-table Meta facts store."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meta_fact import MetaFact


IDENTITY_COLUMNS = (
    "connection_id",
    "level",
    "entity_id",
    "metric_date",
    "attribution_setting",
)


class SqliteMetaFactRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_many(self, rows: Iterable[dict[str, Any]]) -> int:
        """Insert or replace mutable values for each daily fact identity."""
        values = list(rows)
        if not values:
            return 0

        now = datetime.utcnow()
        for row in values:
            row.setdefault("created_at", now)
            row["updated_at"] = now

        statement = sqlite_insert(MetaFact).values(values)
        mutable_columns = {
            column.name: getattr(statement.excluded, column.name)
            for column in MetaFact.__table__.columns
            if column.name not in {"id", "created_at", *IDENTITY_COLUMNS}
        }
        statement = statement.on_conflict_do_update(
            index_elements=list(IDENTITY_COLUMNS),
            set_=mutable_columns,
        )
        await self.session.execute(statement)
        return len(values)
