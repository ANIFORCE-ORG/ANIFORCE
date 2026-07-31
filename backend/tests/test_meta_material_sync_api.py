from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.api.v1 import materials as material_api
from app.api.v1.materials import MetaMaterialSyncRequest, sync_meta_materials
from app.config.database import Base
from app.models import PlatformConnection, SubAccountBinding, User
from app.services.meta_material_sync import ImportedMaterialMedia, MetaMaterialAsset


class FakeSource:
    async def list_assets(self, ad_account_id: str, asset_types: set[str]):
        return [
            MetaMaterialAsset(
                asset_type="image",
                external_asset_id="account:image-1",
                image_hash="hash-1",
                name="Image One",
                source_url="https://meta.example/image.jpg",
            )
        ]


class FakeImporter:
    async def import_media(self, asset: MetaMaterialAsset, user_id: str):
        return ImportedMaterialMedia(
            original_url="https://oss.example/image.jpg",
            storage_object_key="materials/user-1/image.jpg",
            thumbnail_url="https://oss.example/image.jpg",
            content_type="image/jpeg",
            checksum_sha256="a" * 64,
            size=128,
            format="JPG",
        )


async def _seed(session) -> None:
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
    session.add(
        SubAccountBinding(
            id="binding-1",
            parent_connection_id="connection-1",
            sub_account_name="Account One",
            sub_account_id="act_123",
            status="active",
        )
    )
    await session.commit()


def test_sync_endpoint_requires_bound_account_before_meta_call() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        async with maker() as session:
            await _seed(session)
            with pytest.raises(HTTPException) as exc_info:
                await sync_meta_materials(
                    request=MetaMaterialSyncRequest(
                        connection_id="connection-1",
                        ad_account_id="act_999",
                    ),
                    current_user={"id": "user-1"},
                    session=session,
                )
            assert exc_info.value.status_code == 404
            assert "not bound" in exc_info.value.detail
        await engine.dispose()

    asyncio.run(scenario())


def test_sync_endpoint_runs_for_owned_connection_and_bound_account(monkeypatch) -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        async with maker() as session:
            await _seed(session)
            monkeypatch.setattr(material_api.settings, "META_APP_ID", "app-id")
            monkeypatch.setattr(material_api.settings, "META_APP_SECRET", "app-secret")
            monkeypatch.setattr(material_api, "MetaSdkMaterialSource", lambda **_: FakeSource())
            monkeypatch.setattr(material_api, "OssMaterialMediaImporter", FakeImporter)

            result = await sync_meta_materials(
                request=MetaMaterialSyncRequest(
                    connection_id="connection-1",
                    ad_account_id="123",
                    asset_types=["image"],
                ),
                current_user={"id": "user-1"},
                session=session,
            )

            assert result["status"] == "succeeded"
            assert result["ad_account_id"] == "act_123"
            assert result["asset_types"] == ["image"]
            assert result["created_count"] == 1
            assert result["reused_count"] == 0
        await engine.dispose()

    asyncio.run(scenario())
