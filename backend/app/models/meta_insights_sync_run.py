"""Execution record for one user-triggered Meta Insights synchronization."""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class MetaInsightsSyncRun(Base):
    """One synchronous AdSet Insights read for one bound ad account."""

    __tablename__ = "meta_insights_sync_runs"
    __table_args__ = (
        Index(
            "ix_meta_insights_sync_runs_account_started",
            "connection_id",
            "account_id",
            "level",
            "started_at",
        ),
        Index("ix_meta_insights_sync_runs_user_status", "user_id", "status"),
        Index(
            "uq_meta_insights_sync_runs_running_account_level",
            "connection_id",
            "account_id",
            "level",
            unique=True,
            sqlite_where=text("status = 'running'"),
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("platform_connections.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[str] = mapped_column(String(100), nullable=False)
    account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="adset")
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    requested_since: Mapped[date] = mapped_column(Date, nullable=False)
    requested_until: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="running")
    rows_written: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
