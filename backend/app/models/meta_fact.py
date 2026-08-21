"""Normalized daily facts imported from Meta Insights."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class MetaFact(Base):
    """One account/campaign/ad set/ad daily fact row.

    The level column keeps the first implementation intentionally simple. External
    IDs are scoped by connection and parent snapshot fields remain auditable.
    """

    __tablename__ = "meta_facts"
    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "level",
            "entity_id",
            "metric_date",
            "attribution_setting",
            name="uq_meta_facts_identity",
        ),
        Index("ix_meta_facts_connection_date", "connection_id", "metric_date"),
        Index("ix_meta_facts_account_level_date", "account_id", "level", "metric_date"),
        Index("ix_meta_facts_entity", "level", "entity_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("platform_connections.id", ondelete="CASCADE"), nullable=False
    )

    level: Mapped[str] = mapped_column(String(16), nullable=False)
    account_id: Mapped[str] = mapped_column(String(100), nullable=False)
    account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    business_manager_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parent_entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    parent_entity_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    date_stop: Mapped[date | None] = mapped_column(Date, nullable=True)
    attribution_setting: Mapped[str] = mapped_column(String(100), nullable=False, default="default")
    account_currency: Mapped[str | None] = mapped_column(String(12), nullable=True)
    account_timezone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    objective: Mapped[str | None] = mapped_column(String(100), nullable=True)
    optimization_goal: Mapped[str | None] = mapped_column(String(100), nullable=True)

    impressions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reach: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frequency: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    clicks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    inline_link_clicks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spend: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    ctr: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    cpc: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    cpm: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)

    actions_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    action_values_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    cost_per_action_type_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    conversion_values_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    raw_payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="accessible_with_rows")
    sync_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
