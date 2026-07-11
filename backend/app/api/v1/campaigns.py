"""广告投放管理 API"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.protocols import CampaignRepository, MaterialRepository, ProjectRepository
from app.repositories.factory import get_campaign_repo, get_material_repo, get_project_repo
from app.repositories.impl.sqlite_session_state_repo import SqliteSessionStateRepository
from app.config.database import get_db
from app.api.deps import get_current_user
from app.services.idempotency_service import IDEMPOTENCY_HEADER, IdempotencyService
from app.services.session_state_mutation import record_entity_change

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
    # 平台连接
    connection_id: str | None = None
    # Meta Campaign 特定字段
    account_id: str | None = None
    objective: str | None = None
    buying_type: str | None = None
    special_ad_categories: str | None = None
    special_ad_category_country: str | None = None
    promoted_object: str | None = None
    ab_test: str | None = None
    campaign_budget_optimization: str | None = None
    budget_type: str | None = None
    budget_schedule_specs: str | None = None
    pacing_type: str | None = None
    bid_strategy: str | None = None
    spend_limit: float | None = None
    start_date: str | None = None
    end_date: str | None = None


class UpdateCampaignRequest(BaseModel):
    """更新广告计划请求模型"""
    name: str | None = None
    platform: str | None = None
    budget: float | None = None
    status: str | None = None
    material_ids: list[str] | None = None
    # 平台连接
    connection_id: str | None = None
    # Meta Campaign 特定字段
    account_id: str | None = None
    objective: str | None = None
    buying_type: str | None = None
    special_ad_categories: str | None = None
    special_ad_category_country: str | None = None
    promoted_object: str | None = None
    ab_test: str | None = None
    campaign_budget_optimization: str | None = None
    budget_type: str | None = None
    budget_schedule_specs: str | None = None
    pacing_type: str | None = None
    bid_strategy: str | None = None
    spend_limit: float | None = None
    start_date: str | None = None
    end_date: str | None = None


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
    http_request: Request,
    request: CreateCampaignRequest,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    session: AsyncSession = Depends(get_db),
):
    """创建新广告投放"""
    idempotency_key = http_request.headers.get(IDEMPOTENCY_HEADER)
    idempotency = IdempotencyService(session)
    cached = await idempotency.get_response(current_user["id"], idempotency_key)
    if cached is not None:
        return cached

    # 验证项目权限
    project = await project_repo.get_by_id(request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    campaign = await campaign_repo.create(
        project_id=request.project_id,
        name=request.name,
        platform=request.platform,
        budget=request.budget,
        status=request.status or "draft",
        material_ids=request.material_ids or [],
        connection_id=request.connection_id,
        account_id=request.account_id,
        objective=request.objective,
        buying_type=request.buying_type,
        special_ad_categories=request.special_ad_categories,
        special_ad_category_country=request.special_ad_category_country,
        promoted_object=request.promoted_object,
        ab_test=request.ab_test,
        campaign_budget_optimization=request.campaign_budget_optimization,
        budget_type=request.budget_type,
        budget_schedule_specs=request.budget_schedule_specs,
        pacing_type=request.pacing_type,
        bid_strategy=request.bid_strategy,
        spend_limit=request.spend_limit,
        start_date=request.start_date,
        end_date=request.end_date,
    )

    session_id = http_request.headers.get("X-Agent-Session-Id")
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
            run_id=http_request.headers.get("X-Agent-Run-Id"),
            tool_call_id=http_request.headers.get("X-Agent-Tool-Call-Id"),
            linked_entity_updates={"project_id": campaign["project_id"], "campaign_ids": campaign_ids},
        )

    await idempotency.save_response(
        current_user["id"],
        idempotency_key,
        http_request.method,
        str(http_request.url.path),
        campaign,
    )
    # 提交事务以确保数据持久化
    await session.commit()

    return campaign


@router.put("/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    request: UpdateCampaignRequest,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    session: AsyncSession = Depends(get_db),
):
    """更新广告投放"""
    campaign = await campaign_repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # 验证权限
    project = await project_repo.get_by_id(campaign["project_id"])
    if not project or project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 准备更新数据，只更新非 None 的字段
    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.platform is not None:
        update_data["platform"] = request.platform
    if request.budget is not None:
        update_data["budget"] = request.budget
    if request.status is not None:
        update_data["status"] = request.status
    if request.material_ids is not None:
        update_data["material_ids"] = request.material_ids
    if request.connection_id is not None:
        update_data["connection_id"] = request.connection_id
    if request.account_id is not None:
        update_data["account_id"] = request.account_id
    if request.objective is not None:
        update_data["objective"] = request.objective
    if request.buying_type is not None:
        update_data["buying_type"] = request.buying_type
    if request.special_ad_categories is not None:
        update_data["special_ad_categories"] = request.special_ad_categories
    if request.special_ad_category_country is not None:
        update_data["special_ad_category_country"] = request.special_ad_category_country
    if request.promoted_object is not None:
        update_data["promoted_object"] = request.promoted_object
    if request.ab_test is not None:
        update_data["ab_test"] = request.ab_test
    if request.campaign_budget_optimization is not None:
        update_data["campaign_budget_optimization"] = request.campaign_budget_optimization
    if request.budget_type is not None:
        update_data["budget_type"] = request.budget_type
    if request.budget_schedule_specs is not None:
        update_data["budget_schedule_specs"] = request.budget_schedule_specs
    if request.pacing_type is not None:
        update_data["pacing_type"] = request.pacing_type
    if request.bid_strategy is not None:
        update_data["bid_strategy"] = request.bid_strategy
    if request.spend_limit is not None:
        update_data["spend_limit"] = request.spend_limit
    if request.start_date is not None:
        update_data["start_date"] = request.start_date
    if request.end_date is not None:
        update_data["end_date"] = request.end_date

    # 调用 repository 更新方法
    updated_campaign = await campaign_repo.update(campaign_id, **update_data)
    await session.commit()

    return updated_campaign


@router.put("/{campaign_id}/status")
async def update_campaign_status(
    campaign_id: str,
    http_request: Request,
    request: UpdateStatusRequest,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    session: AsyncSession = Depends(get_db),
):
    """更新广告投放状态"""
    idempotency_key = http_request.headers.get(IDEMPOTENCY_HEADER)
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

    await campaign_repo.update_status(campaign_id, request.status)
    session_id = http_request.headers.get("X-Agent-Session-Id")
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
            new_value={"name": campaign.get("name"), "status": request.status},
            run_id=http_request.headers.get("X-Agent-Run-Id"),
            tool_call_id=http_request.headers.get("X-Agent-Tool-Call-Id"),
            rollbackable=True,
        )
    response = {"message": "Campaign status updated successfully"}
    await idempotency.save_response(
        current_user["id"],
        idempotency_key,
        http_request.method,
        str(http_request.url.path),
        response,
    )
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
    material_repo: MaterialRepository = Depends(get_material_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """添加素材到广告投放，并原子更新双向关系。"""
    campaign = await campaign_repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    project = await project_repo.get_by_id(campaign["project_id"])
    if not project or project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    material = await material_repo.get_by_id(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    if material["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    await campaign_repo.add_material(campaign_id, material_id)
    await material_repo.add_to_campaign(material_id, campaign_id)
    return {"message": "Material added to campaign successfully"}


@router.delete("/{campaign_id}/materials/{material_id}")
async def remove_material_from_campaign(
    campaign_id: str,
    material_id: str,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    material_repo: MaterialRepository = Depends(get_material_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """从广告投放移除素材，并原子更新双向关系。"""
    campaign = await campaign_repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    project = await project_repo.get_by_id(campaign["project_id"])
    if not project or project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    material = await material_repo.get_by_id(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    if material["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    await campaign_repo.remove_material(campaign_id, material_id)
    await material_repo.remove_from_campaign(material_id, campaign_id)
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
