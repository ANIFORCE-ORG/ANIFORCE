"""Provider interface for publishing material files to advertising platforms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.models import PlatformConnection


@dataclass(frozen=True)
class PublishedPlatformAsset:
    asset_type: str
    external_asset_id: str
    image_hash: str | None
    name: str | None
    remote_status: str | None
    remote_url: str | None


@dataclass(frozen=True)
class PlatformAssetState:
    remote_status: str | None
    normalized_status: str
    remote_url: str | None = None
    remote_thumbnail_url: str | None = None
    error_message: str | None = None


class PlatformAssetNotFound(RuntimeError):
    pass


class MaterialPlatformProvider(Protocol):
    async def publish(
        self, *, material: dict[str, Any], ad_account_id: str, asset_type: str
    ) -> PublishedPlatformAsset: ...

    async def delete(
        self, *, ad_account_id: str, asset_type: str, external_asset_id: str
    ) -> None: ...

    async def get_state(
        self, *, ad_account_id: str, asset_type: str, external_asset_id: str
    ) -> PlatformAssetState: ...


def create_material_platform_provider(connection: PlatformConnection) -> MaterialPlatformProvider:
    if connection.platform == "Meta":
        from app.services.meta_material_publisher import MetaMaterialPublisher

        if not connection.access_token:
            raise ValueError("Meta connection credentials are incomplete")
        app_id = connection.account_id
        app_secret = connection.account_secret
        if not app_secret:
            from app.config.settings import get_settings

            settings = get_settings()
            app_id = settings.META_APP_ID
            app_secret = settings.META_APP_SECRET
        if not app_id or not app_secret:
            raise ValueError("Meta connection app credentials are incomplete")
        return MetaMaterialPublisher(
            access_token=connection.access_token,
            app_id=app_id,
            app_secret=app_secret,
        )
    raise ValueError(f"Platform provider not implemented: {connection.platform}")


def normalize_platform_status(value: str | None) -> str:
    normalized = (value or "").lower()
    if normalized in {"active", "ready", "completed", "published", "success"}:
        return "ready"
    if normalized in {"processing", "pending", "uploading", "in_progress"}:
        return "processing"
    if normalized in {"failed", "error", "rejected", "disapproved", "deleted"}:
        return "failed"
    return "unknown"
