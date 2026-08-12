from __future__ import annotations

import asyncio
import sys
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
from app.models.material import MaterialStatus, MaterialType
from app.services.meta_material_sync import (
    ImportedMaterialMedia,
    MetaMaterialAsset,
    MetaMaterialSyncService,
)


class RenamedImageSource:
    async def list_assets(self, ad_account_id: str, asset_types: set[str]):
        return [
            MetaMaterialAsset(
                asset_type="image",
                external_asset_id="123:shared-hash",
                image_hash="shared-hash",
                name="Current Meta image",
                source_url="https://meta.example/current.jpg",
                status="ACTIVE",
            )
        ]


class UnexpectedImporter:
    async def import_media(self, asset: MetaMaterialAsset, user_id: str):
        raise AssertionError("An existing account image must not be imported again")


def test_sync_reconciles_same_account_image_when_external_id_changes() -> None:
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
            session.add(
                Material(
                    id="material-1",
                    user_id="user-1",
                    name="Imported image",
                    type=MaterialType.A_SEGMENT,
                    status=MaterialStatus.READY,
                    url="https://oss.example/image.jpg",
                    media_kind="image",
                )
            )
            session.add(
                MaterialPlatformAsset(
                    id="asset-1",
                    material_id="material-1",
                    user_id="user-1",
                    connection_id="connection-1",
                    platform="Meta",
                    ad_account_id="act_123",
                    asset_type="image",
                    external_asset_id="shared-hash",
                    image_hash="shared-hash",
                )
            )
            await session.commit()

            service = MetaMaterialSyncService(
                session=session,
                source=RenamedImageSource(),
                media_importer=UnexpectedImporter(),
            )
            result = await service.sync_account(
                user_id="user-1",
                connection_id="connection-1",
                ad_account_id="act_123",
                asset_types={"image"},
            )
            await session.commit()

            assert result["status"] == "succeeded"
            assert result["updated_count"] == 1
            assert result["failed_count"] == 0
            assert await session.scalar(select(func.count()).select_from(Material)) == 1
            assert await session.scalar(
                select(func.count()).select_from(MaterialPlatformAsset)
            ) == 1
            platform_asset = await session.get(MaterialPlatformAsset, "asset-1")
            assert platform_asset is not None
            assert platform_asset.external_asset_id == "123:shared-hash"
            assert platform_asset.remote_name == "Current Meta image"

        await engine.dispose()

    asyncio.run(scenario())


def test_meta_source_timeout_does_not_hold_sqlite_writer_lock(tmp_path: Path) -> None:
    class HangingSource:
        def __init__(self) -> None:
            self.started = asyncio.Event()

        async def list_assets(self, ad_account_id: str, asset_types: set[str]):
            self.started.set()
            await asyncio.sleep(10)
            return []

    async def scenario() -> None:
        database_path = tmp_path / "meta-timeout.db"
        engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        maker = async_sessionmaker(engine, expire_on_commit=False)

        async with maker() as setup_session:
            setup_session.add(User(id="user-1", email="u@example.com", password_hash="hash"))
            setup_session.add(
                PlatformConnection(
                    id="connection-1",
                    user_id="user-1",
                    platform="Meta",
                    account_id="meta-user-1",
                    access_token="token",
                    status="active",
                )
            )
            await setup_session.commit()

        source = HangingSource()
        async with maker() as sync_session:
            service = MetaMaterialSyncService(
                session=sync_session,
                source=source,
                media_importer=UnexpectedImporter(),
                source_timeout_seconds=0.1,
            )
            sync_task = asyncio.create_task(
                service.sync_account(
                    user_id="user-1",
                    connection_id="connection-1",
                    ad_account_id="act_123",
                    asset_types={"image"},
                )
            )
            await source.started.wait()

            async with maker() as unrelated_session:
                unrelated_session.add(
                    User(id="user-2", email="other@example.com", password_hash="hash")
                )
                await asyncio.wait_for(unrelated_session.commit(), timeout=0.5)

            result = await sync_task
            await sync_session.commit()
            assert result["status"] == "failed"
            assert result["failed_count"] == 1
            assert "timed out after 0.1 seconds" in result["error_summary"]

        async with maker() as verification_session:
            assert await verification_session.scalar(
                select(func.count()).select_from(MaterialSyncRun)
            ) == 1
            assert await verification_session.scalar(
                select(func.count()).select_from(User)
            ) == 2

        await engine.dispose()

    asyncio.run(scenario())


def test_sync_isolates_one_asset_database_failure() -> None:
    class TwoImageSource:
        async def list_assets(self, ad_account_id: str, asset_types: set[str]):
            return [
                MetaMaterialAsset(
                    asset_type="image",
                    external_asset_id="broken-image",
                    image_hash="broken-hash",
                    name="Broken image",
                    source_url="https://meta.example/broken.jpg",
                ),
                MetaMaterialAsset(
                    asset_type="image",
                    external_asset_id="new-image",
                    image_hash="new-hash",
                    name="New image",
                    source_url="https://meta.example/new.jpg",
                ),
            ]

    class FakeImporter:
        async def import_media(self, asset: MetaMaterialAsset, user_id: str):
            return ImportedMaterialMedia(
                original_url=f"https://oss.example/{asset.external_asset_id}.jpg",
                storage_object_key=f"materials/{asset.external_asset_id}.jpg",
                thumbnail_url=f"https://oss.example/{asset.external_asset_id}.jpg",
                content_type="image/jpeg",
                checksum_sha256="a" * 64,
                size=128,
                format="JPG",
            )

    class FailingFirstAssetService(MetaMaterialSyncService):
        async def _upsert_asset(self, **kwargs):
            asset = kwargs["asset"]
            if asset.external_asset_id == "broken-image":
                self.session.add(
                    MaterialPlatformAsset(
                        material_id="material-1",
                        user_id="user-1",
                        connection_id="connection-1",
                        platform="Meta",
                        ad_account_id="act_123",
                        asset_type="image",
                        external_asset_id="conflicting-image",
                    )
                )
                await self.session.flush()
            return await super()._upsert_asset(**kwargs)

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
            session.add(
                Material(
                    id="material-1",
                    user_id="user-1",
                    name="Existing image",
                    type=MaterialType.A_SEGMENT,
                    status=MaterialStatus.READY,
                    url="https://oss.example/existing.jpg",
                    media_kind="image",
                )
            )
            session.add(
                MaterialPlatformAsset(
                    id="asset-1",
                    material_id="material-1",
                    user_id="user-1",
                    connection_id="connection-1",
                    platform="Meta",
                    ad_account_id="act_123",
                    asset_type="image",
                    external_asset_id="existing-image",
                )
            )
            await session.commit()

            service = FailingFirstAssetService(
                session=session,
                source=TwoImageSource(),
                media_importer=FakeImporter(),
            )
            result = await service.sync_account(
                user_id="user-1",
                connection_id="connection-1",
                ad_account_id="act_123",
                asset_types={"image"},
            )
            await session.commit()

            assert result["status"] == "partially_succeeded"
            assert result["created_count"] == 1
            assert result["failed_count"] == 1
            assert await session.scalar(select(func.count()).select_from(Material)) == 2
            assert await session.scalar(
                select(func.count()).select_from(MaterialPlatformAsset)
            ) == 2
            assert await session.scalar(
                select(func.count()).select_from(MaterialSyncRunItem)
            ) == 2

        await engine.dispose()

    asyncio.run(scenario())
