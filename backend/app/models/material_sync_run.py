"""Execution record for one account-scoped material synchronization."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class MaterialSyncRun(Base):
    """One synchronization of one platform connection and ad account."""

    __tablename__ = "material_sync_runs"
    __table_args__ = (
        Index(
            "ix_material_sync_runs_account_started",
            "connection_id",
            "ad_account_id",
            "started_at",
        ),
        Index("ix_material_sync_runs_user_status", "user_id", "status"),
        Index("ix_material_sync_runs_user_direction", "user_id", "direction", "started_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    connection_id: Mapped[str | None] = mapped_column(
        ForeignKey("platform_connections.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    ad_account_id: Mapped[str] = mapped_column(String(100), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False, default="import")
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="manual"
    )
    asset_types: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    discovered_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reused_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processing_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
