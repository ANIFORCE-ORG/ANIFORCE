from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.config.database import Base
from app.models import (
    Material,
    MaterialPlatformAsset,
    MaterialSyncRun,
    MaterialSyncRunItem,
    PlatformConnection,
    User,
)
from app.services.meta_material_sync import (
    ImportedMaterialMedia,
    MetaMaterialAsset,
    MetaMaterialSyncService,
    _normalize_image,
    _sanitize_error_message,
    _normalize_video,
)


ASSETS = [
    MetaMaterialAsset(
        asset_type="image",
        external_asset_id="account-a:image-1",
        image_hash="hash-1",
        name="Image One",
        source_url="https://meta.example/image-1.jpg",
        thumbnail_url="https://meta.example/image-1-thumb.jpg",
        status="ACTIVE",
        width=1200,
        height=1200,
    ),
    MetaMaterialAsset(
        asset_type="video",
        external_asset_id="video-1",
        name="Video One",
        source_url="https://meta.example/video-1.mp4",
        thumbnail_url="https://meta.example/video-1-thumb.jpg",
        status="ready",
        width=1080,
        height=1920,
        duration=12.6,
    ),
]


class FakeSource:
    async def list_assets(self, ad_account_id: str, asset_types: set[str]):
        return [asset for asset in ASSETS if asset.asset_type in asset_types]


class FakeImporter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def import_media(self, asset: MetaMaterialAsset, user_id: str):
        self.calls.append(asset.external_asset_id)
        suffix = "mp4" if asset.asset_type == "video" else "jpg"
        return ImportedMaterialMedia(
            original_url=f"https://oss.example/{user_id}/{asset.external_asset_id}.{suffix}",
            storage_object_key=f"materials/{user_id}/{asset.external_asset_id}.{suffix}",
            thumbnail_url=f"https://oss.example/{user_id}/{asset.external_asset_id}-thumb.jpg",
            content_type=f"{asset.asset_type}/{suffix}",
            checksum_sha256=("a" if asset.asset_type == "image" else "b") * 64,
            size=1024,
            format=suffix.upper(),
        )


def test_sync_is_idempotent_and_reuses_materials_across_accounts() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(engine, expire_on_commit=False)

        async with maker() as session:
            session.add(User(id="user-1", email="u@example.com", password_hash="hash"))
            session.add(
                PlatformConnection(
                    id="connection-1",
                    user_id="user-1",
                    platform="Meta",
                    account_id="meta-user-1",
                    access_token="token",
                    status="active",
                )
            )
            await session.commit()

            importer = FakeImporter()
            service = MetaMaterialSyncService(session, FakeSource(), importer)
            first = await service.sync_account(
                user_id="user-1",
                connection_id="connection-1",
                ad_account_id="act-account-a",
                asset_types={"image", "video"},
            )
            await session.commit()

            assert first["status"] == "succeeded"
            assert first["created_count"] == 2
            assert first["updated_count"] == 0
            assert importer.calls == ["account-a:image-1", "video-1"]

            second = await service.sync_account(
                user_id="user-1",
                connection_id="connection-1",
                ad_account_id="act-account-a",
                asset_types={"image", "video"},
            )
            await session.commit()

            assert second["status"] == "succeeded"
            assert second["created_count"] == 0
            assert second["updated_count"] == 0
            assert second["skipped_count"] == 2
            assert len(importer.calls) == 2

            image_material = await session.scalar(
                select(Material).where(Material.media_kind == "image")
            )
            image_material.lifecycle_status = "archived"
            image_material.archived_at = datetime.utcnow()
            await session.commit()
            restored = await service.sync_account(
                user_id="user-1",
                connection_id="connection-1",
                ad_account_id="act-account-a",
                asset_types={"image"},
            )
            await session.commit()
            await session.refresh(image_material)
            assert restored["updated_count"] == 1
            assert image_material.lifecycle_status == "active"
            assert image_material.archived_at is None

            third = await service.sync_account(
                user_id="user-1",
                connection_id="connection-1",
                ad_account_id="act-account-b",
                asset_types={"image", "video"},
            )
            await session.commit()

            assert third["created_count"] == 0
            assert third["reused_count"] == 2
            assert len(importer.calls) == 2
            assert await session.scalar(select(func.count()).select_from(Material)) == 2
            assert await session.scalar(select(func.count()).select_from(MaterialPlatformAsset)) == 4
            assert await session.scalar(select(func.count()).select_from(MaterialSyncRun)) == 4
            assert await session.scalar(select(func.count()).select_from(MaterialSyncRunItem)) == 7

            materials = (await session.scalars(select(Material))).all()
            assert {item.mime_type for item in materials} == {"image/jpg", "video/mp4"}
            assert all(item.storage_object_key for item in materials)
            assert all(item.checksum_sha256 for item in materials)

        await engine.dispose()

    asyncio.run(scenario())


def test_sync_recreates_material_for_detached_platform_asset() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(engine, expire_on_commit=False)

        async with maker() as session:
            session.add(User(id="user-1", email="u@example.com", password_hash="hash"))
            session.add(
                PlatformConnection(
                    id="connection-1",
                    user_id="user-1",
                    platform="Meta",
                    account_id="meta-user-1",
                    access_token="token",
                    status="active",
                )
            )
            await session.commit()
            importer = FakeImporter()
            service = MetaMaterialSyncService(session, FakeSource(), importer)
            await service.sync_account(
                user_id="user-1",
                connection_id="connection-1",
                ad_account_id="act-account-a",
                asset_types={"image"},
            )
            await session.commit()

            platform_asset = await session.scalar(select(MaterialPlatformAsset))
            original_material_id = platform_asset.material_id
            original_material = await session.get(Material, original_material_id)
            platform_asset.material_id = None
            await session.delete(original_material)
            await session.commit()

            result = await service.sync_account(
                user_id="user-1",
                connection_id="connection-1",
                ad_account_id="act-account-a",
                asset_types={"image"},
            )
            await session.commit()
            await session.refresh(platform_asset)

            assert result["created_count"] == 1
            assert platform_asset.material_id is not None
            assert platform_asset.material_id != original_material_id
            assert await session.get(Material, platform_asset.material_id) is not None
            assert importer.calls == ["account-a:image-1", "account-a:image-1"]

        await engine.dispose()

    asyncio.run(scenario())


def test_sync_error_message_redacts_meta_credentials() -> None:
    token = "EAA" + "a" * 40
    proof = "b" * 64
    message = _sanitize_error_message(
        f"GET https://graph.facebook.com/adimages?access_token={token}"
        f"&appsecret_proof={proof} payload={{'access_token': '{token}'}}"
    )

    assert token not in message
    assert proof not in message
    assert "access_token=[REDACTED]" in message
    assert "appsecret_proof=[REDACTED]" in message


def test_normalizes_meta_image_and_video_fields() -> None:
    image = _normalize_image({
        "id": "account:image-1",
        "name": "Image",
        "hash": "hash-1",
        "url": "https://meta.example/image.jpg",
        "url_128": "https://meta.example/thumb.jpg",
        "width": "1200",
        "height": 600,
        "created_time": "2026-07-05T15:34:41+0700",
    })
    video = _normalize_video({
        "id": "video-1",
        "title": "Video",
        "source": "https://meta.example/video.mp4",
        "picture": "https://meta.example/poster.jpg",
        "length": "32.4",
        "status": {"video_status": "ready"},
        "format": [
            {"width": 130, "height": 231},
            {"width": 1080, "height": 1920},
        ],
        "updated_time": datetime(2026, 7, 6, 8, 0, 0),
    })

    assert image is not None
    assert image.image_hash == "hash-1"
    assert image.width == 1200
    assert image.remote_created_at == datetime(2026, 7, 5, 15, 34, 41)
    assert video is not None
    assert video.status == "ready"
    assert (video.width, video.height) == (1080, 1920)
    assert video.duration == 32.4
