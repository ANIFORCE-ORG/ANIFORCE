"""Account-scoped Meta material synchronization."""

from __future__ import annotations

import asyncio
import json
import mimetypes
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Material,
    MaterialPlatformAsset,
    MaterialSyncRun,
    MaterialSyncRunItem,
)
from app.models.material import MaterialStatus, MaterialType
from app.services.object_storage import AliyunOssStorageService


@dataclass(frozen=True)
class MetaMaterialAsset:
    asset_type: str
    external_asset_id: str
    name: str
    source_url: str
    thumbnail_url: str | None = None
    image_hash: str | None = None
    status: str | None = None
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    remote_created_at: datetime | None = None
    remote_updated_at: datetime | None = None


@dataclass(frozen=True)
class ImportedMaterialMedia:
    original_url: str
    storage_object_key: str
    thumbnail_url: str | None
    content_type: str
    checksum_sha256: str
    size: int
    format: str


class MetaMaterialSource(Protocol):
    async def list_assets(
        self, ad_account_id: str, asset_types: set[str]
    ) -> list[MetaMaterialAsset]: ...


class MaterialMediaImporter(Protocol):
    async def import_media(
        self, asset: MetaMaterialAsset, user_id: str
    ) -> ImportedMaterialMedia: ...


class MetaSdkMaterialSource:
    """Read image and video assets through the Facebook Business SDK."""

    def __init__(self, access_token: str, app_id: str, app_secret: str) -> None:
        self.access_token = access_token
        self.app_id = app_id
        self.app_secret = app_secret

    async def list_assets(
        self, ad_account_id: str, asset_types: set[str]
    ) -> list[MetaMaterialAsset]:
        return await asyncio.to_thread(self._list_assets, ad_account_id, asset_types)

    def _list_assets(
        self, ad_account_id: str, asset_types: set[str]
    ) -> list[MetaMaterialAsset]:
        from facebook_business.api import FacebookAdsApi
        from facebook_business.session import FacebookSession
        from facebook_business.adobjects.adaccount import AdAccount
        from facebook_business.adobjects.adimage import AdImage
        from facebook_business.adobjects.advideo import AdVideo

        api = FacebookAdsApi(
            FacebookSession(self.app_id, self.app_secret, self.access_token)
        )
        normalized_account_id = (
            ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
        )
        account = AdAccount(normalized_account_id, api=api)
        assets: list[MetaMaterialAsset] = []

        if "image" in asset_types:
            images = account.get_ad_images(fields=[
                AdImage.Field.id,
                AdImage.Field.name,
                AdImage.Field.hash,
                AdImage.Field.url,
                AdImage.Field.url_128,
                AdImage.Field.height,
                AdImage.Field.width,
                AdImage.Field.created_time,
                AdImage.Field.updated_time,
                AdImage.Field.status,
            ])
            assets.extend(
                asset
                for image in images
                if (asset := _normalize_image(image)) is not None
            )

        if "video" in asset_types:
            videos = account.get_ad_videos(fields=[
                AdVideo.Field.id,
                AdVideo.Field.title,
                AdVideo.Field.length,
                AdVideo.Field.source,
                AdVideo.Field.picture,
                AdVideo.Field.format,
                AdVideo.Field.created_time,
                AdVideo.Field.updated_time,
                AdVideo.Field.status,
            ])
            assets.extend(
                asset
                for video in videos
                if (asset := _normalize_video(video)) is not None
            )

        return assets


class OssMaterialMediaImporter:
    """Copy expiring Meta media URLs into the application's OSS bucket."""

    def __init__(self, max_bytes: int = 500 * 1024 * 1024) -> None:
        self.storage = AliyunOssStorageService()
        self.max_bytes = max_bytes

    async def import_media(
        self, asset: MetaMaterialAsset, user_id: str
    ) -> ImportedMaterialMedia:
        data, content_type = await self._download(asset.source_url)
        filename = _remote_filename(asset, content_type)
        uploaded = await asyncio.to_thread(
            self.storage.upload_bytes,
            data=data,
            filename=filename,
            content_type=content_type,
            user_id=user_id,
            prefix="materials/meta",
        )

        thumbnail_url = None
        if asset.thumbnail_url and asset.thumbnail_url != asset.source_url:
            try:
                thumbnail_data, thumbnail_type = await self._download(asset.thumbnail_url)
                thumbnail = await asyncio.to_thread(
                    self.storage.upload_bytes,
                    data=thumbnail_data,
                    filename=f"{Path(filename).stem}_thumbnail.jpg",
                    content_type=thumbnail_type,
                    user_id=user_id,
                    prefix="materials/meta-thumbnails",
                )
                thumbnail_url = thumbnail.url
            except (httpx.HTTPError, ValueError):
                thumbnail_url = None

        if asset.asset_type == "image" and not thumbnail_url:
            thumbnail_url = uploaded.url

        suffix = Path(filename).suffix.lstrip(".").upper()
        return ImportedMaterialMedia(
            original_url=uploaded.url,
            storage_object_key=uploaded.object_key,
            thumbnail_url=thumbnail_url,
            content_type=uploaded.content_type,
            checksum_sha256=uploaded.checksum_sha256,
            size=uploaded.size,
            format=suffix or "UNKNOWN",
        )

    async def _download(self, url: str) -> tuple[bytes, str]:
        async with httpx.AsyncClient(follow_redirects=True, timeout=90.0) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                content_length = int(response.headers.get("content-length", "0") or 0)
                if content_length > self.max_bytes:
                    raise ValueError("Meta material exceeds import size limit")
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise ValueError("Meta material exceeds import size limit")
                    chunks.append(chunk)
                content_type = response.headers.get("content-type", "").split(";", 1)[0]
                return b"".join(chunks), content_type or "application/octet-stream"


class MetaMaterialSyncService:
    """Synchronize one Meta ad account into the canonical material library."""

    def __init__(
        self,
        session: AsyncSession,
        source: MetaMaterialSource,
        media_importer: MaterialMediaImporter,
    ) -> None:
        self.session = session
        self.source = source
        self.media_importer = media_importer

    async def sync_account(
        self,
        *,
        user_id: str,
        connection_id: str,
        ad_account_id: str,
        asset_types: set[str],
        ad_account_name: str | None = None,
        trigger_type: str = "manual",
    ) -> dict:
        invalid_types = asset_types - {"image", "video"}
        if not asset_types or invalid_types:
            raise ValueError("asset_types must contain image and/or video")

        run = MaterialSyncRun(
            user_id=user_id,
            connection_id=connection_id,
            ad_account_id=ad_account_id,
            direction="import",
            platform="Meta",
            trigger_type=trigger_type,
            asset_types=json.dumps(sorted(asset_types)),
            status="running",
        )
        self.session.add(run)
        await self.session.flush()

        try:
            assets = await self.source.list_assets(ad_account_id, asset_types)
        except Exception as exc:
            run.status = "failed"
            run.failed_count = 1
            run.error_summary = _sanitize_error_message(exc)[:2000]
            run.finished_at = datetime.utcnow()
            await self.session.flush()
            return _run_result(run)

        run.discovered_count = len(assets)
        errors: list[str] = []
        for asset in assets:
            try:
                action, material_id, platform_asset_id = await self._upsert_asset(
                    user_id=user_id,
                    connection_id=connection_id,
                    ad_account_id=ad_account_id,
                    ad_account_name=ad_account_name,
                    asset=asset,
                )
                if action == "created":
                    run.created_count += 1
                elif action == "reused":
                    run.reused_count += 1
                elif action == "updated":
                    run.updated_count += 1
                else:
                    run.skipped_count += 1
                self._add_run_item(
                    run=run,
                    asset=asset,
                    action=action,
                    material_id=material_id,
                    platform_asset_id=platform_asset_id,
                )
            except Exception as exc:
                run.failed_count += 1
                error_message = _sanitize_error_message(exc)[:2000]
                errors.append(
                    f"{asset.asset_type}:{asset.external_asset_id}: {error_message}"
                )
                self._add_run_item(
                    run=run,
                    asset=asset,
                    action="failed",
                    error_message=error_message,
                )

        if run.failed_count == 0:
            run.status = "succeeded"
        elif run.created_count or run.reused_count or run.updated_count or run.skipped_count:
            run.status = "partially_succeeded"
        else:
            run.status = "failed"
        run.error_summary = "\n".join(errors)[:2000] or None
        run.finished_at = datetime.utcnow()
        await self.session.flush()
        return _run_result(run)

    async def _upsert_asset(
        self,
        *,
        user_id: str,
        connection_id: str,
        ad_account_id: str,
        ad_account_name: str | None,
        asset: MetaMaterialAsset,
    ) -> tuple[str, str, str]:
        existing = await self.session.scalar(
            select(MaterialPlatformAsset).where(
                MaterialPlatformAsset.connection_id == connection_id,
                MaterialPlatformAsset.ad_account_id == ad_account_id,
                MaterialPlatformAsset.asset_type == asset.asset_type,
                MaterialPlatformAsset.external_asset_id == asset.external_asset_id,
            )
        )
        if existing:
            changed = _update_platform_asset(existing, asset)
            return (
                "updated" if changed else "skipped",
                existing.material_id,
                existing.id,
            )

        reusable_material_id = await self._find_reusable_material(user_id, asset)
        if reusable_material_id:
            material_id = reusable_material_id
            action = "reused"
        else:
            imported = await self.media_importer.import_media(asset, user_id)
            material = Material(
                user_id=user_id,
                name=asset.name,
                type=(
                    MaterialType.FULL_VIDEO
                    if asset.asset_type == "video"
                    else MaterialType.A_SEGMENT
                ),
                status=MaterialStatus.READY,
                url=imported.original_url,
                storage_object_key=imported.storage_object_key,
                mime_type=imported.content_type,
                checksum_sha256=imported.checksum_sha256,
                thumbnail_url=imported.thumbnail_url,
                poster_url=(
                    imported.thumbnail_url if asset.asset_type == "video" else None
                ),
                preview_url=imported.thumbnail_url,
                tags=json.dumps(["Meta同步"], ensure_ascii=False),
                media_kind=asset.asset_type,
                format=imported.format,
                width=asset.width,
                height=asset.height,
                ratio=_ratio_label(asset.width, asset.height),
                source="meta_import",
                platforms=json.dumps(["Meta"]),
                review_status=asset.status,
                source_account=ad_account_id,
                duration=(round(asset.duration) if asset.duration else None),
                file_size=imported.size,
            )
            self.session.add(material)
            await self.session.flush()
            material_id = material.id
            action = "created"

        platform_asset = MaterialPlatformAsset(
            material_id=material_id,
            user_id=user_id,
            connection_id=connection_id,
            platform="Meta",
            created_via="import",
            ad_account_id=ad_account_id,
            ad_account_name=ad_account_name,
            asset_type=asset.asset_type,
            external_asset_id=asset.external_asset_id,
            image_hash=asset.image_hash,
        )
        _update_platform_asset(platform_asset, asset)
        self.session.add(platform_asset)
        await self.session.flush()
        return action, material_id, platform_asset.id

    def _add_run_item(
        self,
        *,
        run: MaterialSyncRun,
        asset: MetaMaterialAsset,
        action: str,
        material_id: str | None = None,
        platform_asset_id: str | None = None,
        error_message: str | None = None,
    ) -> None:
        self.session.add(
            MaterialSyncRunItem(
                run_id=run.id,
                asset_type=asset.asset_type,
                external_asset_id=asset.external_asset_id,
                remote_name=asset.name,
                action=action,
                material_id=material_id,
                platform_asset_id=platform_asset_id,
                error_message=error_message,
            )
        )

    async def _find_reusable_material(
        self, user_id: str, asset: MetaMaterialAsset
    ) -> str | None:
        identity_filter = (
            MaterialPlatformAsset.image_hash == asset.image_hash
            if asset.asset_type == "image" and asset.image_hash
            else MaterialPlatformAsset.external_asset_id == asset.external_asset_id
        )
        return await self.session.scalar(
            select(MaterialPlatformAsset.material_id)
            .where(
                MaterialPlatformAsset.user_id == user_id,
                MaterialPlatformAsset.platform == "Meta",
                MaterialPlatformAsset.asset_type == asset.asset_type,
                identity_filter,
            )
            .limit(1)
        )


def _normalize_image(image: object) -> MetaMaterialAsset | None:
    image_hash = _field(image, "hash")
    external_id = _field(image, "id") or image_hash
    source_url = _field(image, "url")
    if not external_id or not source_url:
        return None
    return MetaMaterialAsset(
        asset_type="image",
        external_asset_id=str(external_id),
        image_hash=str(image_hash) if image_hash else None,
        name=str(_field(image, "name") or f"Meta image {external_id}"),
        source_url=str(source_url),
        thumbnail_url=_optional_str(_field(image, "url_128")),
        status=_optional_str(_field(image, "status")),
        width=_optional_int(_field(image, "width")),
        height=_optional_int(_field(image, "height")),
        remote_created_at=_parse_meta_datetime(_field(image, "created_time")),
        remote_updated_at=_parse_meta_datetime(_field(image, "updated_time")),
    )


def _normalize_video(video: object) -> MetaMaterialAsset | None:
    external_id = _field(video, "id")
    source_url = _field(video, "source")
    if not external_id or not source_url:
        return None
    width, height = _largest_video_format(_field(video, "format"))
    status = _field(video, "status")
    if hasattr(status, "get"):
        status = status.get("video_status") or status.get("status")
    return MetaMaterialAsset(
        asset_type="video",
        external_asset_id=str(external_id),
        name=str(_field(video, "title") or f"Meta video {external_id}"),
        source_url=str(source_url),
        thumbnail_url=_optional_str(_field(video, "picture")),
        status=_optional_str(status),
        width=width,
        height=height,
        duration=_optional_float(_field(video, "length")),
        remote_created_at=_parse_meta_datetime(_field(video, "created_time")),
        remote_updated_at=_parse_meta_datetime(_field(video, "updated_time")),
    )


def _update_platform_asset(
    platform_asset: MaterialPlatformAsset, asset: MetaMaterialAsset
) -> bool:
    remote_fields = {
        "image_hash": asset.image_hash,
        "remote_name": asset.name,
        "remote_status": asset.status,
        "normalized_status": _normalize_remote_status(asset.status),
        "remote_url": asset.source_url,
        "remote_thumbnail_url": asset.thumbnail_url,
        "remote_created_at": asset.remote_created_at,
        "remote_updated_at": asset.remote_updated_at,
    }
    changed = any(
        getattr(platform_asset, field_name) != value
        for field_name, value in remote_fields.items()
    )
    for field_name, value in remote_fields.items():
        setattr(platform_asset, field_name, value)
    platform_asset.last_seen_at = datetime.utcnow()
    return changed


def _normalize_remote_status(value: str | None) -> str:
    from app.services.material_platform_provider import normalize_platform_status

    return normalize_platform_status(value)


def _sanitize_error_message(error: Exception | str) -> str:
    message = str(error)
    message = re.sub(
        r"(?i)((?:access_token|appsecret_proof)=)[^&\s'\"]+",
        r"\1[REDACTED]",
        message,
    )
    message = re.sub(
        r"(?i)((?:['\"]?(?:access_token|appsecret_proof)['\"]?)\s*:\s*['\"])[^'\"]+",
        r"\1[REDACTED]",
        message,
    )
    return re.sub(r"\bEAA[A-Za-z0-9]{20,}\b", "[REDACTED_META_TOKEN]", message)


def _run_result(run: MaterialSyncRun) -> dict:
    return {
        "run_id": run.id,
        "status": run.status,
        "connection_id": run.connection_id,
        "ad_account_id": run.ad_account_id,
        "discovered_count": run.discovered_count,
        "asset_types": json.loads(run.asset_types),
        "created_count": run.created_count,
        "reused_count": run.reused_count,
        "updated_count": run.updated_count,
        "skipped_count": run.skipped_count,
        "failed_count": run.failed_count,
        "error_summary": run.error_summary,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


def _field(value: object, name: str) -> object | None:
    if hasattr(value, "get"):
        return value.get(name)
    if isinstance(value, dict):
        return value.get(name)
    return None


def _parse_meta_datetime(value: object | None) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        return None


def _largest_video_format(value: object | None) -> tuple[int | None, int | None]:
    if not isinstance(value, (list, tuple)):
        return None, None
    dimensions = [
        (_optional_int(_field(item, "width")), _optional_int(_field(item, "height")))
        for item in value
    ]
    valid = [(width, height) for width, height in dimensions if width and height]
    return max(valid, key=lambda item: item[0] * item[1]) if valid else (None, None)


def _ratio_label(width: int | None, height: int | None) -> str | None:
    if not width or not height:
        return None
    ratio = width / height
    for label, expected in (("9:16", 9 / 16), ("1:1", 1), ("4:5", 4 / 5), ("16:9", 16 / 9)):
        if abs(ratio - expected) < 0.03:
            return label
    return f"{width}:{height}"


def _remote_filename(asset: MetaMaterialAsset, content_type: str) -> str:
    suffix = Path(urlparse(asset.source_url).path).suffix
    if not suffix:
        suffix = mimetypes.guess_extension(content_type) or (
            ".mp4" if asset.asset_type == "video" else ".jpg"
        )
    stem = Path(asset.name).stem or f"meta-{asset.external_asset_id}"
    return f"{stem}{suffix}"


def _optional_str(value: object | None) -> str | None:
    return str(value) if value is not None else None


def _optional_int(value: object | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _optional_float(value: object | None) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
