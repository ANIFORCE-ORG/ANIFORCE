"""素材管理 API"""
import os
import base64
import json
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.protocols import CampaignRepository, MaterialRepository, ProjectRepository
from app.models import (
    MaterialSyncRun,
    MaterialSyncRunItem,
    MaterialPlatformAsset,
    PlatformConnection,
    SubAccountBinding,
)
from app.repositories.factory import get_campaign_repo, get_material_repo, get_project_repo
from app.api.deps import get_current_user
from app.config.database import get_db
from app.config.settings import get_settings
from app.services.idempotency_service import IDEMPOTENCY_HEADER, IdempotencyService
from app.services.meta_material_sync import (
    MetaMaterialSyncService,
    MetaSdkMaterialSource,
    OssMaterialMediaImporter,
    _sanitize_error_message,
)
from app.services.material_platform_provider import (
    PlatformAssetNotFound,
    create_material_platform_provider,
    normalize_platform_status,
)
from app.services.object_storage import AliyunOssStorageService, ObjectStorageError

router = APIRouter(prefix="/materials", tags=["materials"])
settings = get_settings()


async def reconcile_stale_material_sync_runs(
    session: AsyncSession,
    *,
    user_id: str | None = None,
    timeout: timedelta = timedelta(minutes=30),
) -> int:
    """Close transfer runs left open by a crashed request or worker."""
    cutoff = datetime.utcnow() - timeout
    conditions = [
        MaterialSyncRun.status == "running",
        MaterialSyncRun.started_at < cutoff,
        MaterialSyncRun.finished_at.is_(None),
    ]
    if user_id is not None:
        conditions.append(MaterialSyncRun.user_id == user_id)
    runs = (
        await session.scalars(
            select(MaterialSyncRun).where(*conditions)
        )
    ).all()
    for run in runs:
        run.status = "failed"
        run.finished_at = datetime.utcnow()
        run.error_summary = "任务因服务中断未完成，请重新发起传输"
    if runs:
        await session.flush()
    return len(runs)


# 图像存储路径
IMAGES_DIR = Path(__file__).parent.parent.parent.parent / "data" / "images"
FRONTEND_CREATIVE_IMAGES_DIR = (
    Path(__file__).resolve().parents[4]
    / "frontend"
    / "packages"
    / "main-app"
    / "public"
    / "images"
    / "creatives"
)


class CreateMaterialRequest(BaseModel):
    name: str
    type: str
    url: str
    thumbnail_url: str | None = None
    project_ids: list[str] | None = None
    campaign_ids: list[str] | None = None
    tags: list[str] | None = None
    ctr_estimate: float | None = None


class MetaMaterialSyncRequest(BaseModel):
    connection_id: str
    ad_account_id: str
    asset_types: list[str] = Field(default_factory=lambda: ["image", "video"])


class MetaMaterialPublishRequest(BaseModel):
    platform: str = "Meta"
    connection_id: str
    ad_account_id: str
    asset_type: str


class UpdateMaterialRequest(BaseModel):
    name: str | None = None
    status: str | None = None
    thumbnail_url: str | None = None
    poster_url: str | None = None
    preview_url: str | None = None
    ctr_estimate: float | None = None
    tags: list[str] | None = None
    media_kind: str | None = None
    format: str | None = None
    width: int | None = None
    height: int | None = None
    ratio: str | None = None
    source: str | None = None
    creator: str | None = None
    rights: str | None = None
    platforms: list[str] | None = None
    review_status: str | None = None
    source_account: str | None = None
    placements: list[str] | None = None
    score: int | None = None
    fatigue: int | None = None
    duration: int | None = None
    file_size: int | None = None


@router.get("")
async def list_materials(
    project_id: str | None = None,
    campaign_id: str | None = None,
    type: str | None = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    session: AsyncSession = Depends(get_db),
):
    """获取素材列表"""
    if project_id:
        project = await project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Permission denied")
        materials = await material_repo.list_by_project(project_id, limit=limit)
    elif campaign_id:
        campaign = await campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        project = await project_repo.get_by_id(campaign["project_id"])
        if not project or project["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Permission denied")
        materials = await material_repo.list_by_campaign(campaign_id, limit=limit)
    else:
        materials = await material_repo.list_by_user(
            current_user["id"], type=type, limit=limit
        )
    
    if not hasattr(session, "scalars"):
        return {"materials": materials}

    asset_rows = (
        await session.scalars(
            select(MaterialPlatformAsset).where(
                MaterialPlatformAsset.user_id == current_user["id"],
                MaterialPlatformAsset.normalized_status != "missing",
            )
        )
    ).all()
    assets_by_material: dict[str, list[dict]] = {}
    for asset in asset_rows:
        if not asset.material_id:
            continue
        assets_by_material.setdefault(asset.material_id, []).append({
            "id": asset.id,
            "connection_id": asset.connection_id,
            "platform": asset.platform,
            "ad_account_id": asset.ad_account_id,
            "ad_account_name": asset.ad_account_name,
            "asset_type": asset.asset_type,
            "external_asset_id": asset.external_asset_id,
            "image_hash": asset.image_hash,
            "remote_name": asset.remote_name,
            "remote_status": asset.remote_status,
            "normalized_status": asset.normalized_status,
            "remote_url": asset.remote_url,
            "remote_thumbnail_url": asset.remote_thumbnail_url,
            "last_seen_at": asset.last_seen_at.isoformat(),
            "last_verified_at": asset.last_verified_at.isoformat() if asset.last_verified_at else None,
            "last_error": asset.last_error,
        })
    for material in materials:
        material["platform_assets"] = assets_by_material.get(material["id"], [])
    return {"materials": materials}


@router.get("/{material_id}")
async def get_material(
    material_id: str,
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
    session: AsyncSession = Depends(get_db),
):
    """获取素材详情"""
    material = await material_repo.get_by_id(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    # 验证权限
    if material["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    assets = (
        await session.scalars(
            select(MaterialPlatformAsset).where(
                MaterialPlatformAsset.material_id == material_id,
                MaterialPlatformAsset.user_id == current_user["id"],
                MaterialPlatformAsset.normalized_status != "missing",
            )
        )
    ).all()
    material["platform_assets"] = [_serialize_platform_asset(asset) for asset in assets]
    return material


@router.patch("/{material_id}")
async def update_material(
    material_id: str,
    request: UpdateMaterialRequest,
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
    session: AsyncSession = Depends(get_db),
):
    """更新素材基础信息"""
    material = await material_repo.get_by_id(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    if material["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        return material

    try:
        updated = await material_repo.update(material_id, **update_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await session.commit()
    return updated


@router.post("/sync/meta")
async def sync_meta_materials(
    request: MetaMaterialSyncRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Import image and video assets from one authorized Meta ad account."""
    connection = await session.scalar(
        select(PlatformConnection).where(
            PlatformConnection.id == request.connection_id,
            PlatformConnection.user_id == current_user["id"],
        )
    )
    if not connection:
        raise HTTPException(status_code=404, detail="Meta connection not found")
    if connection.platform != "Meta":
        raise HTTPException(status_code=400, detail="Connection is not a Meta connection")
    if connection.status != "active" or not connection.access_token:
        raise HTTPException(status_code=400, detail="Meta connection is not authorized")

    bindings = (
        await session.scalars(
            select(SubAccountBinding).where(
                SubAccountBinding.parent_connection_id == connection.id
            )
        )
    ).all()
    normalized_account_id = request.ad_account_id.removeprefix("act_")
    binding = next(
        (
            item
            for item in bindings
            if item.sub_account_id.removeprefix("act_") == normalized_account_id
        ),
        None,
    )
    if not binding:
        raise HTTPException(status_code=404, detail="Meta ad account is not bound to this connection")
    if binding.status != "active":
        raise HTTPException(status_code=400, detail="Meta ad account is not active")
    # account_id identifies the OAuth subject, not the Meta application.
    app_id = settings.META_APP_ID
    app_secret = settings.META_APP_SECRET
    if not app_id or not app_secret:
        raise HTTPException(status_code=500, detail="Meta connection app configuration is missing")

    await reconcile_stale_material_sync_runs(session, user_id=current_user["id"])
    try:
        service = MetaMaterialSyncService(
            session=session,
            source=MetaSdkMaterialSource(
                access_token=connection.access_token,
                app_id=app_id,
                app_secret=app_secret,
            ),
            media_importer=OssMaterialMediaImporter(),
        )
        result = await service.sync_account(
            user_id=current_user["id"],
            connection_id=connection.id,
            ad_account_id=binding.sub_account_id,
            ad_account_name=binding.sub_account_name,
            asset_types=set(request.asset_types),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ObjectStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    await session.commit()
    return result


@router.post("/{material_id}/meta/publish")
@router.post("/{material_id}/platform-assets/publish")
async def publish_material_to_meta(
    material_id: str,
    request: MetaMaterialPublishRequest,
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
    session: AsyncSession = Depends(get_db),
):
    """Publish one Material to one account through its platform provider."""
    material = await material_repo.get_by_id(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    if material["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    if request.asset_type not in {"image", "video"}:
        raise HTTPException(status_code=400, detail="asset_type must be image or video")
    media_kind = material.get("media_kind") or (
        "video" if str(material.get("mime_type") or "").startswith("video/") else "image"
    )
    if media_kind != request.asset_type:
        raise HTTPException(status_code=400, detail=f"Material media kind is {media_kind}, not {request.asset_type}")

    connection, binding = await _get_platform_binding(
        session, current_user["id"], request.connection_id, request.ad_account_id
    )
    await reconcile_stale_material_sync_runs(session, user_id=current_user["id"])
    if request.platform and request.platform != connection.platform:
        raise HTTPException(status_code=400, detail="Request platform does not match connection")
    try:
        provider = create_material_platform_provider(connection)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    existing = await session.scalar(
        select(MaterialPlatformAsset).where(
            MaterialPlatformAsset.material_id == material_id,
            MaterialPlatformAsset.platform == connection.platform,
            MaterialPlatformAsset.ad_account_id == binding.sub_account_id,
            MaterialPlatformAsset.asset_type == request.asset_type,
        )
    )
    if existing and existing.normalized_status != "failed":
        try:
            state = await provider.get_state(
                ad_account_id=binding.sub_account_id,
                asset_type=existing.asset_type,
                external_asset_id=existing.image_hash or existing.external_asset_id,
            )
            existing.remote_status = state.remote_status
            existing.normalized_status = state.normalized_status
            existing.remote_url = state.remote_url or existing.remote_url
            existing.remote_thumbnail_url = state.remote_thumbnail_url or existing.remote_thumbnail_url
            existing.last_verified_at = datetime.utcnow()
            existing.last_error = (
                _sanitize_error_message(state.error_message)[:2000]
                if state.error_message
                else None
            )
        except PlatformAssetNotFound:
            await session.delete(existing)
            await session.commit()
            existing = None
        except Exception as exc:
            message = _sanitize_error_message(exc)[:2000]
            existing.last_error = message
            existing.normalized_status = "unknown"
            await session.commit()
            raise HTTPException(
                status_code=502,
                detail=f"无法确认已有平台素材的状态，请稍后重试：{message}",
            ) from exc
        if existing and existing.normalized_status in {"ready", "processing"}:
            await _record_export_result(session, current_user["id"], connection, binding.sub_account_id, material_id, existing, "reused")
            return _platform_asset_result(existing, action="reused")
        if existing and existing.normalized_status == "unknown":
            raise HTTPException(
                status_code=502,
                detail=f"Meta 返回了无法识别的素材状态：{existing.remote_status or 'empty'}",
            )

    run = MaterialSyncRun(
        user_id=current_user["id"],
        connection_id=connection.id,
        ad_account_id=binding.sub_account_id,
        direction="export",
        platform=connection.platform,
        trigger_type="manual",
        asset_types=json.dumps([request.asset_type]),
        status="running",
        discovered_count=1,
    )
    asset = existing or MaterialPlatformAsset(
        material_id=material_id,
        user_id=current_user["id"],
        connection_id=connection.id,
        platform=connection.platform,
        created_via="publish",
        ad_account_id=binding.sub_account_id,
        ad_account_name=binding.sub_account_name,
        asset_type=request.asset_type,
        external_asset_id=f"pending:{uuid4()}",
        remote_status="uploading",
        normalized_status="processing",
    )
    if existing:
        asset.connection_id = connection.id
        asset.remote_status = "uploading"
        asset.normalized_status = "processing"
        asset.last_error = None
    session.add(run)
    session.add(asset)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        concurrent = await session.scalar(
            select(MaterialPlatformAsset).where(
                MaterialPlatformAsset.material_id == material_id,
                MaterialPlatformAsset.platform == connection.platform,
                MaterialPlatformAsset.ad_account_id == binding.sub_account_id,
                MaterialPlatformAsset.asset_type == request.asset_type,
            )
        )
        if concurrent:
            return _platform_asset_result(concurrent, action="reused")
        raise

    try:
        published = await provider.publish(
            material=material,
            ad_account_id=binding.sub_account_id,
            asset_type=request.asset_type,
        )
        asset.external_asset_id = published.external_asset_id
        asset.image_hash = published.image_hash
        asset.remote_name = published.name
        asset.remote_status = published.remote_status or "ready"
        asset.normalized_status = normalize_platform_status(asset.remote_status)
        asset.remote_url = published.remote_url
        asset.last_seen_at = datetime.utcnow()
        asset.last_verified_at = datetime.utcnow()
        run.processing_count = 1 if asset.normalized_status == "processing" else 0
        run.created_count = 1
        run.status = "processing" if run.processing_count else "succeeded"
        run.finished_at = None if run.processing_count else datetime.utcnow()
        session.add(MaterialSyncRunItem(
            run_id=run.id,
            asset_type=asset.asset_type,
            external_asset_id=asset.external_asset_id,
            remote_name=asset.remote_name,
            action="created",
            status=asset.normalized_status,
            material_id=material_id,
            platform_asset_id=asset.id,
        ))
        await session.commit()
        await session.refresh(asset)
        result = _platform_asset_result(asset, action="created")
        result["run_id"] = run.id
        return result
    except Exception as exc:
        message = _sanitize_error_message(exc)[:2000]
        asset.remote_status = "failed"
        asset.normalized_status = "failed"
        asset.last_error = message
        run.status = "failed"
        run.failed_count = 1
        run.error_summary = message
        run.finished_at = datetime.utcnow()
        session.add(MaterialSyncRunItem(
            run_id=run.id,
            asset_type=request.asset_type,
            external_asset_id=asset.external_asset_id,
            action="failed",
            status="failed",
            error_message=message,
            material_id=material_id,
            platform_asset_id=asset.id,
        ))
        await session.commit()
        raise HTTPException(status_code=502, detail=message) from exc


@router.post("/{material_id}/platform-assets/{asset_id}/refresh")
async def refresh_material_platform_asset(
    material_id: str,
    asset_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    asset = await session.scalar(select(MaterialPlatformAsset).where(
        MaterialPlatformAsset.id == asset_id,
        MaterialPlatformAsset.material_id == material_id,
        MaterialPlatformAsset.user_id == current_user["id"],
    ))
    if not asset:
        raise HTTPException(status_code=404, detail="Platform material asset not found")
    connection = await session.scalar(select(PlatformConnection).where(
        PlatformConnection.id == asset.connection_id,
        PlatformConnection.user_id == current_user["id"],
    ))
    if not connection:
        raise HTTPException(status_code=409, detail="Platform connection is unavailable")
    try:
        state = await create_material_platform_provider(connection).get_state(
            ad_account_id=asset.ad_account_id,
            asset_type=asset.asset_type,
            external_asset_id=asset.image_hash or asset.external_asset_id,
        )
        asset.remote_status = state.remote_status
        asset.normalized_status = state.normalized_status
        asset.remote_url = state.remote_url or asset.remote_url
        asset.remote_thumbnail_url = state.remote_thumbnail_url or asset.remote_thumbnail_url
        asset.last_verified_at = datetime.utcnow()
        asset.last_error = (
            _sanitize_error_message(state.error_message)[:2000]
            if state.error_message
            else None
        )
        if state.normalized_status != "processing":
            item = await session.scalar(
                select(MaterialSyncRunItem)
                .where(MaterialSyncRunItem.platform_asset_id == asset.id)
                .order_by(MaterialSyncRunItem.processed_at.desc())
                .limit(1)
            )
            if item:
                item.status = "completed" if state.normalized_status == "ready" else "failed"
                item.updated_at = datetime.utcnow()
                run = await session.scalar(select(MaterialSyncRun).where(MaterialSyncRun.id == item.run_id))
                if run and run.status == "processing":
                    run.processing_count = 0
                    run.failed_count = 1 if state.normalized_status == "failed" else 0
                    run.status = "failed" if state.normalized_status == "failed" else "succeeded"
                    run.finished_at = datetime.utcnow()
        await session.commit()
        return _platform_asset_result(asset, action="updated")
    except Exception as exc:
        message = _sanitize_error_message(exc)[:2000]
        asset.last_error = message
        await session.commit()
        raise HTTPException(status_code=502, detail=message) from exc


async def _get_platform_binding(
    session: AsyncSession, user_id: str, connection_id: str, ad_account_id: str
):
    connection = await session.scalar(
        select(PlatformConnection).where(
            PlatformConnection.id == connection_id,
            PlatformConnection.user_id == user_id,
        )
    )
    if not connection:
        raise HTTPException(status_code=404, detail="Platform connection not found")
    if connection.status != "active" or not connection.access_token:
        raise HTTPException(status_code=400, detail="Platform connection is not authorized")
    normalized = ad_account_id.removeprefix("act_")
    bindings = (
        await session.scalars(
            select(SubAccountBinding).where(
                SubAccountBinding.parent_connection_id == connection.id,
                SubAccountBinding.status == "active",
            )
        )
    ).all()
    binding = next(
        (item for item in bindings if item.sub_account_id.removeprefix("act_") == normalized),
        None,
    )
    if not binding:
        raise HTTPException(status_code=404, detail="Advertising account is not bound to this connection")
    return connection, binding


async def _record_export_result(
    session: AsyncSession,
    user_id: str,
    connection: PlatformConnection,
    ad_account_id: str,
    material_id: str,
    asset: MaterialPlatformAsset,
    action: str,
) -> None:
    run = MaterialSyncRun(
        user_id=user_id,
        connection_id=connection.id,
        ad_account_id=ad_account_id,
        direction="export",
        platform=connection.platform,
        trigger_type="manual",
        asset_types=json.dumps([asset.asset_type]),
        status="succeeded",
        discovered_count=1,
        reused_count=1,
        finished_at=datetime.utcnow(),
    )
    session.add(run)
    await session.flush()
    session.add(MaterialSyncRunItem(
        run_id=run.id,
        asset_type=asset.asset_type,
        external_asset_id=asset.external_asset_id,
        remote_name=asset.remote_name,
        action=action,
        status="completed",
        material_id=material_id,
        platform_asset_id=asset.id,
    ))
    await session.commit()


def _serialize_platform_asset(asset: MaterialPlatformAsset) -> dict:
    return {
        "id": asset.id,
        "material_id": asset.material_id,
        "connection_id": asset.connection_id,
        "platform": asset.platform,
        "ad_account_id": asset.ad_account_id,
        "ad_account_name": asset.ad_account_name,
        "asset_type": asset.asset_type,
        "external_asset_id": asset.external_asset_id,
        "image_hash": asset.image_hash,
        "remote_name": asset.remote_name,
        "remote_status": asset.remote_status,
        "normalized_status": asset.normalized_status,
        "remote_url": asset.remote_url,
        "remote_thumbnail_url": asset.remote_thumbnail_url,
        "last_seen_at": asset.last_seen_at.isoformat(),
        "last_verified_at": asset.last_verified_at.isoformat() if asset.last_verified_at else None,
        "last_error": asset.last_error,
    }


def _platform_asset_result(asset: MaterialPlatformAsset, *, action: str) -> dict:
    return {
        "action": action,
        "platform_asset": {
            "id": asset.id,
            "material_id": asset.material_id,
            "connection_id": asset.connection_id,
            "platform": asset.platform,
            "ad_account_id": asset.ad_account_id,
            "ad_account_name": asset.ad_account_name,
            "asset_type": asset.asset_type,
            "external_asset_id": asset.external_asset_id,
            "image_hash": asset.image_hash,
            "remote_name": asset.remote_name,
            "remote_status": asset.remote_status,
            "normalized_status": asset.normalized_status,
            "remote_url": asset.remote_url,
            "remote_thumbnail_url": asset.remote_thumbnail_url,
            "last_verified_at": asset.last_verified_at.isoformat() if asset.last_verified_at else None,
            "last_error": asset.last_error,
        },
    }


@router.get("/sync-runs/{run_id}")
async def get_material_sync_run(
    run_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Return a material sync run owned by the current user."""
    run = await session.scalar(
        select(MaterialSyncRun).where(
            MaterialSyncRun.id == run_id,
            MaterialSyncRun.user_id == current_user["id"],
        )
    )
    if not run:
        raise HTTPException(status_code=404, detail="Material sync run not found")
    items = (
        await session.scalars(
            select(MaterialSyncRunItem)
            .where(MaterialSyncRunItem.run_id == run.id)
            .order_by(MaterialSyncRunItem.processed_at.asc())
        )
    ).all()
    return {
        "run_id": run.id,
        "status": run.status,
        "direction": run.direction,
        "platform": run.platform,
        "connection_id": run.connection_id,
        "ad_account_id": run.ad_account_id,
        "asset_types": json.loads(run.asset_types),
        "discovered_count": run.discovered_count,
        "created_count": run.created_count,
        "reused_count": run.reused_count,
        "updated_count": run.updated_count,
        "skipped_count": run.skipped_count,
        "processing_count": run.processing_count,
        "failed_count": run.failed_count,
        "error_summary": run.error_summary,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "items": [
            {
                "asset_type": item.asset_type,
                "external_asset_id": item.external_asset_id,
                "remote_name": item.remote_name,
                "action": item.action,
                "status": item.status,
                "material_id": item.material_id,
                "platform_asset_id": item.platform_asset_id,
                "error_message": item.error_message,
                "processed_at": item.processed_at.isoformat(),
            }
            for item in items
        ],
    }


@router.get("/{material_id}/image")
async def get_material_image(
    material_id: str,
    thumbnail: bool = False,
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
):
    """获取素材图像（Base64编码）"""
    material = await material_repo.get_by_id(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    # 验证权限
    if material["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # 获取素材路径：缩略图不存在时回退原始素材，兼容视频 MVP 预览。
    image_url = material.get("thumbnail_url") if thumbnail else material.get("url")
    if not image_url:
        image_url = material.get("url")
    if not image_url:
        raise HTTPException(status_code=404, detail="Material file not found")
    
    storage = _try_create_storage()
    if storage:
        object_key = storage.object_key_from_url(image_url)
        if object_key:
            filename = os.path.basename(object_key)
            mime_type = _mime_type_from_filename(filename)
            process = None
            if thumbnail and mime_type.startswith("image/"):
                process = "image/resize,w_160/quality,q_80/format,webp"
            return {
                "material_id": material_id,
                "filename": filename,
                "mime_type": "image/webp" if process else mime_type,
                "size": material.get("file_size") or 0,
                "data": "",
                "url": storage.signed_url(object_key, process=process),
            }

    if image_url.startswith(("http://", "https://")):
        filename = os.path.basename(image_url.split("?", 1)[0])
        mime_type = _mime_type_from_filename(filename)
        return {
            "material_id": material_id,
            "filename": filename,
            "mime_type": mime_type,
            "size": material.get("file_size") or 0,
            "data": "",
            "url": image_url,
        }

    # 从URL中提取文件名
    filename = os.path.basename(image_url)
    image_path = _resolve_local_image_path(image_url)
    
    if not image_path:
        raise HTTPException(status_code=404, detail="Image file not found")
    
    # 读取图像并转换为Base64
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        # 获取文件扩展名以确定MIME类型
        ext = image_path.suffix.lower()
        mime_type = _mime_type_from_filename(image_path.name)
        
        # Base64编码
        base64_data = base64.b64encode(image_data).decode("utf-8")
        
        return {
            "material_id": material_id,
            "filename": filename,
            "mime_type": mime_type,
            "size": len(image_data),
            "data": f"data:{mime_type};base64,{base64_data}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read image: {str(e)}")


@router.get("/images/list")
async def list_available_images(
    current_user: dict = Depends(get_current_user),
):
    """列出所有可用的图像文件"""
    if not IMAGES_DIR.exists():
        return {"images": []}
    
    images = []
    for file_path in IMAGES_DIR.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            images.append({
                "filename": file_path.name,
                "size": file_path.stat().st_size,
                "url": f"/images/{file_path.name}"
            })
    
    return {"images": images}


@router.post("/upload")
async def upload_materials(
    files: Annotated[list[UploadFile], File(description="素材文件，支持图片和视频")],
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
):
    """上传素材文件到 OSS，并创建素材记录。"""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    storage = AliyunOssStorageService()
    materials = []
    uploaded_keys: list[str] = []
    for file in files:
        _validate_upload_file(file)
        try:
            uploaded = await storage.upload_material(file, current_user["id"])
        except ObjectStorageError as exc:
            _cleanup_storage_objects(storage, uploaded_keys)
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except Exception as exc:
            _cleanup_storage_objects(storage, uploaded_keys)
            raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc

        uploaded_keys.append(uploaded.object_key)
        try:
            material = await material_repo.create(
            user_id=current_user["id"],
            name=Path(file.filename or uploaded.object_key).stem,
            original_filename=file.filename,
            type=_material_type_from_content_type(uploaded.content_type),
            url=uploaded.url,
            storage_object_key=uploaded.object_key,
            mime_type=uploaded.content_type,
            checksum_sha256=uploaded.checksum_sha256,
            thumbnail_url=uploaded.url if uploaded.content_type.startswith("image/") else None,
            preview_url=uploaded.url if uploaded.content_type.startswith("image/") else None,
            media_kind="video" if uploaded.content_type.startswith("video/") else "image",
            format=Path(file.filename or uploaded.object_key).suffix.lstrip(".").upper(),
            source="oss_upload",
            lifecycle_status="active",
            processing_status="ready",
            project_ids=[],
            campaign_ids=[],
            tags=["uploaded"],
                file_size=uploaded.size,
            )
        except Exception:
            _cleanup_storage_objects(storage, uploaded_keys)
            raise
        materials.append(material)

    return {"materials": materials}


@router.post("/upload-with-metadata")
async def upload_material_with_metadata(
    file: Annotated[UploadFile, File(description="单个素材文件，支持图片和视频")],
    poster: Annotated[UploadFile | None, File(description="视频封面图")] = None,
    name: Annotated[str | None, Form()] = None,
    status: Annotated[str, Form()] = "ready",
    tags: Annotated[str | None, Form()] = None,
    ctr_estimate: Annotated[float | None, Form()] = None,
    duration: Annotated[int | None, Form()] = None,
    width: Annotated[int | None, Form()] = None,
    height: Annotated[int | None, Form()] = None,
    ratio: Annotated[str | None, Form()] = None,
    format: Annotated[str | None, Form()] = None,
    media_kind: Annotated[str | None, Form()] = None,
    source: Annotated[str | None, Form()] = "oss_upload",
    creator: Annotated[str | None, Form()] = None,
    rights: Annotated[str | None, Form()] = None,
    platforms: Annotated[str | None, Form()] = None,
    review_status: Annotated[str | None, Form()] = "待审核",
    source_account: Annotated[str | None, Form()] = None,
    placements: Annotated[str | None, Form()] = None,
    campaign_ids: Annotated[str | None, Form()] = None,
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
):
    """上传单个素材并保存详情字段。视频封面由前端轻量抽帧后作为 poster 上传。"""
    _validate_upload_file(file)
    if poster:
        _validate_upload_file(poster, image_only=True, max_size=5 * 1024 * 1024)

    storage = AliyunOssStorageService()
    uploaded_keys: list[str] = []
    try:
        uploaded = await storage.upload_material(file, current_user["id"])
        uploaded_keys.append(uploaded.object_key)
        poster_uploaded = None
        if poster:
            poster_uploaded = await storage.upload_material(poster, current_user["id"])
            uploaded_keys.append(poster_uploaded.object_key)
    except ObjectStorageError as exc:
        _cleanup_storage_objects(storage, uploaded_keys)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        _cleanup_storage_objects(storage, uploaded_keys)
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc

    is_image = uploaded.content_type.startswith("image/")
    resolved_media_kind = media_kind or ("video" if uploaded.content_type.startswith("video/") else "image")
    thumbnail_url = poster_uploaded.url if poster_uploaded else (uploaded.url if is_image else None)
    try:
        material = await material_repo.create(
        user_id=current_user["id"],
        name=(name or Path(file.filename or uploaded.object_key).stem).strip(),
        original_filename=file.filename,
        type=_material_type_from_content_type(uploaded.content_type),
        url=uploaded.url,
        storage_object_key=uploaded.object_key,
        mime_type=uploaded.content_type,
        checksum_sha256=uploaded.checksum_sha256,
        thumbnail_url=thumbnail_url,
        poster_url=poster_uploaded.url if poster_uploaded else None,
        preview_url=thumbnail_url,
        project_ids=[],
        campaign_ids=_parse_json_list(campaign_ids),
        tags=_parse_json_list(tags) or ["uploaded"],
        ctr_estimate=ctr_estimate,
        duration=duration,
        file_size=uploaded.size,
        media_kind=resolved_media_kind,
        format=(format or Path(file.filename or uploaded.object_key).suffix.replace(".", "")).upper(),
        width=width,
        height=height,
        ratio=ratio,
        source=source,
        lifecycle_status="active",
        processing_status="ready",
        creator=creator,
        rights=rights,
        platforms=_parse_json_list(platforms),
        review_status=review_status,
        source_account=source_account,
            placements=_parse_json_list(placements),
        )
    except Exception:
        _cleanup_storage_objects(storage, uploaded_keys)
        raise
    return material


@router.post("")
async def create_material(
    http_request: Request,
    request: CreateMaterialRequest,
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
    session: AsyncSession = Depends(get_db),
):
    """创建新素材"""
    idempotency_key = http_request.headers.get(IDEMPOTENCY_HEADER)
    idempotency = IdempotencyService(session)
    cached = await idempotency.get_response(current_user["id"], idempotency_key)
    if cached is not None:
        return cached

    try:
        material = await material_repo.create(
            user_id=current_user["id"],
            name=request.name,
            type=request.type,
            url=request.url,
            thumbnail_url=request.thumbnail_url,
            project_ids=request.project_ids or [],
            campaign_ids=request.campaign_ids or [],
            tags=request.tags or [],
            ctr_estimate=request.ctr_estimate,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await idempotency.save_response(
        current_user["id"],
        idempotency_key,
        http_request.method,
        str(http_request.url.path),
        material,
    )
    await session.commit()
    return material


@router.post("/{material_id}/projects/{project_id}")
async def add_material_to_project(
    material_id: str,
    project_id: str,
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
):
    """添加素材到项目"""
    material = await material_repo.get_by_id(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    if material["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    await material_repo.add_to_project(material_id, project_id)
    return {"message": "Material added to project successfully"}


@router.delete("/{material_id}/projects/{project_id}")
async def remove_material_from_project(
    material_id: str,
    project_id: str,
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
):
    """从项目移除素材"""
    material = await material_repo.get_by_id(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    if material["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    await material_repo.remove_from_project(material_id, project_id)
    return {"message": "Material removed from project successfully"}


def _cleanup_storage_objects(storage: AliyunOssStorageService, object_keys: list[str]) -> None:
    for object_key in object_keys:
        try:
            storage.delete_object(object_key)
        except Exception:
            pass


def _validate_upload_file(
    file: UploadFile,
    image_only: bool = False,
    max_size: int = 100 * 1024 * 1024,
) -> None:
    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "video/mp4",
        "video/quicktime",
    }
    if image_only:
        allowed_types = {content_type for content_type in allowed_types if content_type.startswith("image/")}
    content_type = file.content_type or ""
    if content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {content_type or 'unknown'}")
    size = getattr(file, "size", None)
    if size is not None and size > max_size:
        raise HTTPException(status_code=400, detail="File exceeds 100MB limit")


def _parse_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass
    return [item.strip() for item in value.split(",") if item.strip()]


def _material_type_from_content_type(content_type: str) -> str:
    if content_type.startswith("video/"):
        return "full_video"
    return "a_segment"


def _mime_type_from_filename(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
    }
    return mime_types.get(ext, "application/octet-stream")


def _try_create_storage() -> AliyunOssStorageService | None:
    try:
        return AliyunOssStorageService()
    except ObjectStorageError:
        return None


def _resolve_local_image_path(image_url: str) -> Path | None:
    filename = os.path.basename(image_url)
    candidates = []
    if image_url.startswith("/images/creatives/"):
        candidates.append(FRONTEND_CREATIVE_IMAGES_DIR / filename)
    candidates.extend([
        IMAGES_DIR / filename,
        FRONTEND_CREATIVE_IMAGES_DIR / filename,
    ])
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


@router.delete("/{material_id}")
async def delete_material(
    material_id: str,
    current_user: dict = Depends(get_current_user),
    material_repo: MaterialRepository = Depends(get_material_repo),
    session: AsyncSession = Depends(get_db),
):
    """删除素材"""
    material = await material_repo.get_by_id(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    if material["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    await session.execute(
        update(MaterialPlatformAsset)
        .where(
            MaterialPlatformAsset.material_id == material_id,
            MaterialPlatformAsset.user_id == current_user["id"],
        )
        .values(material_id=None)
    )
    await material_repo.delete(material_id)
    await session.commit()
    object_key = material.get("storage_object_key")
    if object_key:
        storage = _try_create_storage()
        if storage:
            try:
                storage.delete_object(object_key)
            except ObjectStorageError:
                pass
    return {"message": "Material deleted successfully"}
