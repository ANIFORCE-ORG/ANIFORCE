"""SQLite persistence for the single-table Meta facts store."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable

from sqlalchemy import select
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

    async def list_daily_facts(
        self,
        *,
        connection_id: str | list[str],
        since: date,
        until: date,
        level: str = "campaign",
        account_id: str | None = None,
    ) -> list[MetaFact]:
        statement = (
            select(MetaFact)
            .where(MetaFact.connection_id.in_(connection_id) if isinstance(connection_id, list) else MetaFact.connection_id == connection_id)
            .where(MetaFact.level == level)
            .where(MetaFact.metric_date >= since)
            .where(MetaFact.metric_date <= until)
            .order_by(MetaFact.metric_date.asc(), MetaFact.entity_id.asc())
        )
        if account_id is not None:
            statement = statement.where(MetaFact.account_id == account_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
