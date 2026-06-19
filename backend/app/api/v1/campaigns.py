"""广告投放管理 API"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.protocols import CampaignRepository, ProjectRepository
from app.repositories.factory import get_campaign_repo, get_project_repo
from app.repositories.impl.sqlite_session_state_repo import SqliteSessionStateRepository
from app.services.session_state_mutation import record_entity_change
from app.services.idempotency_service import IDEMPOTENCY_HEADER, IdempotencyService
from app.config.database import get_db
from app.api.deps import get_current_user

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class UpdateStatusRequest(BaseModel):
    """更新状态请求模型"""
    status: str


class CreateCampaignRequest(BaseModel):
    """创建广告计划请求模型"""
    project_id: str
    name: str
    platform: str
    budget: float
    status: str | None = "draft"
    material_ids: list[str] | None = None


@router.get("")
async def list_campaigns(
    project_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """获取广告投放列表"""
    if project_id:
        # 验证项目权限
        project = await project_repo.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Permission denied")
        
        campaigns = await campaign_repo.list_by_project(
            project_id=project_id,
            status=status,
            limit=limit
        )
    else:
        # 获取用户所有项目的广告投放
        projects = await project_repo.list_by_user(current_user["id"], limit=100)
        campaigns = []
        for project in projects:
            project_campaigns = await campaign_repo.list_by_project(
                project_id=project["id"],
                status=status,
                limit=limit
            )
            # 添加项目名称
            for campaign in project_campaigns:
                campaign["project_name"] = project["name"]
            campaigns.extend(project_campaigns)
    
    return {"campaigns": campaigns}


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """获取广告投放详情"""
    campaign = await campaign_repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # 验证权限
    project = await project_repo.get_by_id(campaign["project_id"])
    if not project or project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # 添加项目名称
    campaign["project_name"] = project["name"]
    
    return campaign


@router.post("")
async def create_campaign(
    request: Request,
    payload: CreateCampaignRequest,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    session: AsyncSession = Depends(get_db),
):
    """创建新广告投放"""
    idempotency_key = request.headers.get(IDEMPOTENCY_HEADER)
    idempotency = IdempotencyService(session)
    cached = await idempotency.get_response(current_user["id"], idempotency_key)
    if cached is not None:
        return cached

    # 验证项目权限
    project = await project_repo.get_by_id(payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    campaign = await campaign_repo.create(
        project_id=payload.project_id,
        name=payload.name,
        platform=payload.platform,
        budget=payload.budget,
        status=payload.status or "draft",
        material_ids=payload.material_ids or [],
    )
    
    session_id = request.headers.get("X-Agent-Session-Id")
    if session_id:
        state_repo = SqliteSessionStateRepository(session)
        current_state = await state_repo.get(session_id, current_user["id"])
        campaign_ids = []
        if current_state:
            campaign_ids = list((current_state.get("linked_entities") or {}).get("campaign_ids") or [])
        if campaign["id"] not in campaign_ids:
            campaign_ids.append(campaign["id"])
        await record_entity_change(
            repo=state_repo,
            session_id=session_id,
            user_id=current_user["id"],
            entity_type="campaign",
            entity_id=campaign["id"],
            action="created",
            new_value={"name": campaign["name"], "budget": campaign["budget"], "platform": campaign["platform"]},
            run_id=request.headers.get("X-Agent-Run-Id"),
            tool_call_id=request.headers.get("X-Agent-Tool-Call-Id"),
            linked_entity_updates={"project_id": campaign["project_id"], "campaign_ids": campaign_ids},
        )
    await idempotency.save_response(current_user["id"], idempotency_key, request.method, str(request.url.path), campaign)
    # 提交事务以确保数据持久化
    await session.commit()
    
    return campaign


@router.put("/{campaign_id}/status")
async def update_campaign_status(
    campaign_id: str,
    request: Request,
    payload: UpdateStatusRequest,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    session: AsyncSession = Depends(get_db),
):
    """更新广告投放状态"""
    idempotency_key = request.headers.get(IDEMPOTENCY_HEADER)
    idempotency = IdempotencyService(session)
    cached = await idempotency.get_response(current_user["id"], idempotency_key)
    if cached is not None:
        return cached

    campaign = await campaign_repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # 验证权限
    project = await project_repo.get_by_id(campaign["project_id"])
    if not project or project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    await campaign_repo.update_status(campaign_id, payload.status)
    session_id = request.headers.get("X-Agent-Session-Id")
    if session_id:
        await record_entity_change(
            repo=SqliteSessionStateRepository(session),
            session_id=session_id,
            user_id=current_user["id"],
            entity_type="campaign",
            entity_id=campaign_id,
            action="updated",
            field="status",
            old_value=campaign.get("status"),
            new_value={"name": campaign.get("name"), "status": payload.status},
            run_id=request.headers.get("X-Agent-Run-Id"),
            tool_call_id=request.headers.get("X-Agent-Tool-Call-Id"),
            rollbackable=True,
        )
    response = {"message": "Campaign status updated successfully"}
    await idempotency.save_response(current_user["id"], idempotency_key, request.method, str(request.url.path), response)
    await session.commit()  # 提交事务到数据库
    return response


@router.get("/{campaign_id}/materials")
async def get_campaign_materials(
    campaign_id: str,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """获取广告投放的素材列表"""
    campaign = await campaign_repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # 验证权限
    project = await project_repo.get_by_id(campaign["project_id"])
    if not project or project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    materials = await campaign_repo.get_materials(campaign_id)
    return {"materials": materials}


@router.post("/{campaign_id}/materials/{material_id}")
async def add_material_to_campaign(
    campaign_id: str,
    material_id: str,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """添加素材到广告投放"""
    campaign = await campaign_repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # 验证权限
    project = await project_repo.get_by_id(campaign["project_id"])
    if not project or project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    await campaign_repo.add_material(campaign_id, material_id)
    return {"message": "Material added to campaign successfully"}


@router.delete("/{campaign_id}/materials/{material_id}")
async def remove_material_from_campaign(
    campaign_id: str,
    material_id: str,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """从广告投放移除素材"""
    campaign = await campaign_repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # 验证权限
    project = await project_repo.get_by_id(campaign["project_id"])
    if not project or project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    await campaign_repo.remove_material(campaign_id, material_id)
    return {"message": "Material removed from campaign successfully"}


@router.delete("/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """删除广告投放"""
    campaign = await campaign_repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # 验证权限
    project = await project_repo.get_by_id(campaign["project_id"])
    if not project or project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    await campaign_repo.delete(campaign_id)
    return {"message": "Campaign deleted successfully"}
