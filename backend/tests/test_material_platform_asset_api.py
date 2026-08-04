from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.api.v1 import materials as material_api
from app.api.v1.materials import (    MetaMaterialDeleteRequest,
    MetaMaterialPublishRequest,
    delete_material,
    delete_material_meta_asset,
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
    PlatformAssetNotFound,
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

    async def delete(self, **_):
        self.delete_calls += 1

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


def test_publish_refresh_delete_platform_asset_lifecycle(monkeypatch) -> None:
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

            with pytest.raises(HTTPException) as blocked:
                await delete_material("material-1", {"id": "user-1"}, repo, session)
            assert blocked.value.status_code == 409

            deleted = await delete_material_meta_asset(
                "material-1", asset_id,
                MetaMaterialDeleteRequest(platform="Meta", connection_id="connection-1", ad_account_id="123", asset_type="video"),
                {"id": "user-1"}, repo, session,
            )
            assert deleted["action"] == "deleted"
            assert provider.delete_calls == 1
            assert await session.scalar(select(func.count()).select_from(MaterialPlatformAsset)) == 0

            detail = await get_material("material-1", {"id": "user-1"}, repo, session)
            assert detail["platform_assets"] == []

        await engine.dispose()

    asyncio.run(scenario())


def test_delete_treats_already_missing_remote_asset_as_success(monkeypatch) -> None:
    class MissingOnDeleteProvider(FakeProvider):
        async def delete(self, **_):
            self.delete_calls += 1
            raise RuntimeError('Meta returned HTTP 200 with success=false')

        async def get_state(self, **_):
            raise PlatformAssetNotFound('Platform asset no longer exists')

    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        provider = MissingOnDeleteProvider()
        monkeypatch.setattr(material_api, "create_material_platform_provider", lambda _: provider)

        async with maker() as session:
            repo = await _seed(session)
            asset = MaterialPlatformAsset(
                id="asset-missing", material_id="material-1", user_id="user-1",
                connection_id="connection-1", platform="Meta", ad_account_id="act_123",
                ad_account_name="Account One", asset_type="video", external_asset_id="video-missing",
                normalized_status="ready",
            )
            session.add(asset)
            await session.commit()

            deleted = await delete_material_meta_asset(
                "material-1", asset.id,
                MetaMaterialDeleteRequest(
                    platform="Meta", connection_id="connection-1",
                    ad_account_id="123", asset_type="video",
                ),
                {"id": "user-1"}, repo, session,
            )
            assert deleted["action"] == "deleted"
            assert provider.delete_calls == 1
            assert await session.get(MaterialPlatformAsset, asset.id) is None

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
