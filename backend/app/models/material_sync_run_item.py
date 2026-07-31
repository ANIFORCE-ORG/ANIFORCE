"""Per-asset result for a material synchronization run."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class MaterialSyncRunItem(Base):
    """The outcome of processing one remote material asset."""

    __tablename__ = "material_sync_run_items"
    __table_args__ = (
        Index("ix_material_sync_run_items_run_action", "run_id", "action"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        ForeignKey("material_sync_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)
    external_asset_id: Mapped[str] = mapped_column(String(255), nullable=False)
    remote_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    material_id: Mapped[str | None] = mapped_column(
        ForeignKey("materials.id", ondelete="SET NULL"), nullable=True, index=True
    )
    platform_asset_id: Mapped[str | None] = mapped_column(
        ForeignKey("material_platform_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
