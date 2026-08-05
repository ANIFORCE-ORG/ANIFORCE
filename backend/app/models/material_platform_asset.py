"""Platform-specific identity for a material."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class MaterialPlatformAsset(Base):
    """A material as it exists in one external advertising account."""

    __tablename__ = "material_platform_assets"
    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "ad_account_id",
            "asset_type",
            "external_asset_id",
            name="uq_material_platform_asset_identity",
        ),
        Index(
            "ix_material_platform_assets_account",
            "connection_id",
            "ad_account_id",
        ),
        Index(
            "ix_material_platform_assets_dedupe",
            "user_id",
            "platform",
            "asset_type",
            "image_hash",
        ),
        Index(
            "ix_material_platform_assets_status",
            "user_id",
            "platform",
            "normalized_status",
        ),
        Index(
            "uq_material_platform_asset_target",
            "material_id",
            "platform",
            "ad_account_id",
            "asset_type",
            unique=True,
        ),
        Index(
            "uq_material_platform_asset_remote_identity",
            "user_id",
            "platform",
            "ad_account_id",
            "asset_type",
            "external_asset_id",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    material_id: Mapped[str | None] = mapped_column(
        ForeignKey("materials.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    connection_id: Mapped[str | None] = mapped_column(
        ForeignKey("platform_connections.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    created_via: Mapped[str] = mapped_column(String(20), nullable=False, default="import")
    ad_account_id: Mapped[str] = mapped_column(String(100), nullable=False)
    ad_account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)
    external_asset_id: Mapped[str] = mapped_column(String(255), nullable=False)
    image_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    remote_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remote_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    normalized_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    remote_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    remote_thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    remote_created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remote_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
