from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.api.v1 import materials as material_api
from app.api.v1.materials import (
    MetaMaterialPublishRequest,
    reconcile_stale_material_sync_runs,
    delete_material,
    get_material,
    publish_material_to_meta,
    refresh_material_platform_asset,
)
from app.api.v1.platform_auth import delete_connection
from app.config.database import Base
from app.models import Material, MaterialPlatformAsset, MaterialSyncRun, MaterialSyncRunItem, PlatformConnection, SubAccountBinding, User
from app.models.material import MaterialStatus, MaterialType
from app.repositories.impl.sqlite_material_repo import SqliteMaterialRepository
from app.services.material_platform_provider import (
    PlatformAssetState,
    PublishedPlatformAsset,
)


@dataclass
class FakeProvider:
    publish_calls: int = 0
    delete_calls: int = 0

    async def publish(self, **_):
        self.publish_calls += 1
        return PublishedPlatformAsset("video", "video-1", None, "Video", "processing", None)

    async def get_state(self, **_):
        return PlatformAssetState("ready", "ready", remote_url="https://meta.example/video-1.mp4")


async def _seed(session) -> SqliteMaterialRepository:
    session.add(User(id="user-1", email="u@example.com", password_hash="hash"))
    session.add(PlatformConnection(
        id="connection-1", user_id="user-1", platform="Meta", account_id="app-1",
        account_secret="secret", access_token="token", status="active",
    ))
    session.add(SubAccountBinding(
        id="binding-1", parent_connection_id="connection-1", sub_account_name="Account One",
        sub_account_id="act_123", status="active",
    ))
    session.add(Material(
        id="material-1", user_id="user-1", name="Video", type=MaterialType.FULL_VIDEO,
        status=MaterialStatus.READY, lifecycle_status="active", processing_status="ready",
        media_kind="video", mime_type="video/mp4", url="https://oss.example/video.mp4",
    ))
    await session.commit()
    return SqliteMaterialRepository(session)


def test_stale_material_sync_runs_are_reconciled() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        async with maker() as session:
            await _seed(session)
            stale = MaterialSyncRun(
                id="stale-run", user_id="user-1", connection_id="connection-1",
                ad_account_id="act_123", direction="export", platform="Meta",
                asset_types='["video"]', status="running",
                started_at=datetime.utcnow() - timedelta(hours=2),
            )
            fresh = MaterialSyncRun(
                id="fresh-run", user_id="user-1", connection_id="connection-1",
                ad_account_id="act_123", direction="export", platform="Meta",
                asset_types='["video"]', status="running",
                started_at=datetime.utcnow(),
            )
            processing = MaterialSyncRun(
                id="processing-run", user_id="user-1", connection_id="connection-1",
                ad_account_id="act_123", direction="export", platform="Meta",
                asset_types='["video"]', status="processing",
                started_at=datetime.utcnow() - timedelta(hours=2),
            )
            session.add_all([stale, fresh, processing])
            await session.commit()

            count = await reconcile_stale_material_sync_runs(session, timeout=timedelta(minutes=30))
            assert count == 1
            await session.refresh(stale)
            await session.refresh(fresh)
            await session.refresh(processing)
            assert stale.status == "failed"
            assert stale.finished_at is not None
            assert "服务中断" in (stale.error_summary or "")
            assert fresh.status == "running"
            assert processing.status == "processing"
        await engine.dispose()

    asyncio.run(scenario())


def test_publish_and_refresh_platform_asset_lifecycle(monkeypatch) -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        provider = FakeProvider()
        monkeypatch.setattr(material_api, "create_material_platform_provider", lambda _: provider)

        async with maker() as session:
            repo = await _seed(session)
            request = MetaMaterialPublishRequest(
                platform="Meta", connection_id="connection-1", ad_account_id="123", asset_type="video"
            )
            created = await publish_material_to_meta(
                "material-1", request, {"id": "user-1"}, repo, session
            )
            assert created["action"] == "created"
            assert created["platform_asset"]["normalized_status"] == "processing"
            assert provider.publish_calls == 1
            assert await session.scalar(select(func.count()).select_from(MaterialSyncRun)) == 1
            assert await session.scalar(select(func.count()).select_from(MaterialSyncRunItem)) == 1

            reused = await publish_material_to_meta(
                "material-1", request, {"id": "user-1"}, repo, session
            )
            assert reused["action"] == "reused"
            assert provider.publish_calls == 1

            detail = await get_material("material-1", {"id": "user-1"}, repo, session)
            assert len(detail["platform_assets"]) == 1
            asset_id = detail["platform_assets"][0]["id"]

            refreshed = await refresh_material_platform_asset(
                "material-1", asset_id, {"id": "user-1"}, session
            )
            assert refreshed["platform_asset"]["normalized_status"] == "ready"

        await engine.dispose()

    asyncio.run(scenario())


def test_existing_asset_verification_error_is_not_reported_as_reused(monkeypatch) -> None:
    class VerificationErrorProvider(FakeProvider):
        async def get_state(self, **_):
            raise RuntimeError("Meta verification unavailable")

    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        provider = VerificationErrorProvider()
        monkeypatch.setattr(material_api, "create_material_platform_provider", lambda _: provider)

        async with maker() as session:
            repo = await _seed(session)
            asset = MaterialPlatformAsset(
                id="asset-existing", material_id="material-1", user_id="user-1",
                connection_id="connection-1", platform="Meta", ad_account_id="act_123",
                asset_type="video", external_asset_id="video-existing", normalized_status="ready",
            )
            session.add(asset)
            await session.commit()
            request = MetaMaterialPublishRequest(
                platform="Meta", connection_id="connection-1", ad_account_id="123", asset_type="video"
            )

            with pytest.raises(HTTPException) as error:
                await publish_material_to_meta(
                    "material-1", request, {"id": "user-1"}, repo, session
                )
            assert error.value.status_code == 502
            assert "无法确认已有平台素材" in error.value.detail
            await session.refresh(asset)
            assert asset.normalized_status == "unknown"
            assert provider.publish_calls == 0

        await engine.dispose()

    asyncio.run(scenario())


def test_deleting_local_material_detaches_platform_asset_without_remote_delete(monkeypatch) -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        provider = FakeProvider()
        monkeypatch.setattr(material_api, "create_material_platform_provider", lambda _: provider)

        async with maker() as session:
            repo = await _seed(session)
            asset = MaterialPlatformAsset(
                id="asset-detached", material_id="material-1", user_id="user-1",
                connection_id="connection-1", platform="Meta", ad_account_id="act_123",
                ad_account_name="Account One", asset_type="video", external_asset_id="video-remote",
                normalized_status="ready",
            )
            session.add(asset)
            await session.commit()

            result = await delete_material("material-1", {"id": "user-1"}, repo, session)
            assert result["message"] == "Material deleted successfully"
            assert await session.get(Material, "material-1") is None
            await session.refresh(asset)
            assert asset.material_id is None
            assert asset.external_asset_id == "video-remote"
            assert provider.delete_calls == 0

        await engine.dispose()

    asyncio.run(scenario())


def test_deleting_connection_preserves_asset_identity_and_transfer_history() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        async with maker() as session:
            await _seed(session)
            asset = MaterialPlatformAsset(
                id="asset-1", material_id="material-1", user_id="user-1",
                connection_id="connection-1", platform="Meta", ad_account_id="act_123",
                ad_account_name="Account One", asset_type="video", external_asset_id="video-1",
                normalized_status="ready",
            )
            run = MaterialSyncRun(
                id="run-1", user_id="user-1", connection_id="connection-1",
                ad_account_id="act_123", direction="import", platform="Meta",
                asset_types='["video"]', status="succeeded",
            )
            session.add_all([asset, run])
            await session.commit()

            await delete_connection("connection-1", session, {"id": "user-1"})
            await session.refresh(asset)
            await session.refresh(run)
            assert asset.connection_id is None
            assert asset.ad_account_name == "Account One"
            assert run.connection_id is None

        await engine.dispose()

    asyncio.run(scenario())
