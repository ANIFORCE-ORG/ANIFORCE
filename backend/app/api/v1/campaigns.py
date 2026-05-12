"""广告投放管理 API"""
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Metric, PlatformAccount, ProjectPlatformAccount
from app.repositories.protocols import CampaignMaterialRepository, CampaignRepository, MaterialRepository, MetricRepository, ProjectRepository
from app.repositories.factory import get_campaign_material_repo, get_campaign_repo, get_material_repo, get_metric_repo, get_project_repo
from app.config.database import get_db
from app.api.deps import get_current_user
from app.schemas.campaign_material import CampaignMaterialCreate, CampaignMaterialUpdate

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class UpdateStatusRequest(BaseModel):
    """更新状态请求模型"""
    status: str


class CreateCampaignRequest(BaseModel):
    """创建广告计划请求模型"""
    project_id: str
    name: str
    platform: str
    platform_account_id: str | None = None
    budget: float
    budget_type: str | None = "total"
    status: str | None = "draft"
    objective: str | None = None
    bidding_strategy: str | None = None
    target_cpa: float | None = None
    start_date: str | None = None
    end_date: str | None = None
    target_regions: list[str] | None = None
    age_range: dict | None = None
    gender: str | None = None
    target_interests: list[str] | None = None
    material_ids: list[str] | None = None
    auto_optimize_enabled: bool | None = True


class MetricCreateRequest(BaseModel):
    timestamp: str | None = None
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    installs: int = 0
    spend: float = 0
    revenue: float = 0
    ctr: float | None = None
    cvr: float | None = None
    cpa: float | None = None
    cpi: float | None = None
    roi: float | None = None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.fromisoformat(value).date()


def _campaign_duration_days(campaign: dict) -> int:
    start = _parse_date(campaign.get("start_date"))
    end = _parse_date(campaign.get("end_date"))
    if not start or not end:
        return 1
    return max((end - start).days + 1, 1)


def _campaign_elapsed_days(campaign: dict) -> int:
    start = _parse_date(campaign.get("start_date"))
    end = _parse_date(campaign.get("end_date"))
    today = date.today()
    if not start:
        return 1
    effective_end = min(end or today, today)
    return max((effective_end - start).days + 1, 1)


def _budget_snapshot(project: dict, campaigns: list[dict]) -> dict:
    allocated = sum(float(c.get("budget") or 0) for c in campaigns)
    spent = float(project.get("spent") or 0)
    total = float(project.get("total_budget") or 0)
    return {
        "project_total_budget": total,
        "project_spent": spent,
        "project_remaining_budget": max(total - spent, 0),
        "project_allocated_budget": allocated,
        "project_unallocated_budget": max(total - allocated, 0),
        "project_allocation_rate": allocated / total if total else 0,
        "project_spend_rate": spent / total if total else 0,
    }


def _agent_action(campaign: dict, project_snapshot: dict) -> dict:
    budget = float(campaign.get("budget") or 0)
    spent = float(campaign.get("spent") or 0)
    cpi = campaign.get("cpi")
    target_cpa = campaign.get("target_cpa")
    roi = campaign.get("roi")
    spend_rate = spent / budget if budget else 0
    elapsed_rate = _campaign_elapsed_days(campaign) / _campaign_duration_days(campaign)
    pacing_gap = spend_rate - elapsed_rate

    if campaign.get("status") == "review":
        return {"level": "info", "label": "等待审核", "reason": "素材和账户状态通过后再启动放量"}
    if budget and spend_rate >= 0.9:
        return {"level": "warning", "label": "预算接近耗尽", "reason": "剩余计划预算不足 10%，需要补预算或降速"}
    if target_cpa and cpi and cpi > target_cpa * 1.15:
        return {"level": "danger", "label": "降预算观察", "reason": "实际 CPI 已高于目标 15%，建议收窄定向或更换素材"}
    if roi and roi >= 2.0 and project_snapshot["project_unallocated_budget"] > 0:
        return {"level": "success", "label": "可加预算", "reason": "ROI 表现达标且项目仍有未分配预算"}
    if pacing_gap > 0.2:
        return {"level": "warning", "label": "消耗偏快", "reason": "预算节奏高于时间进度，建议检查日限额"}
    if pacing_gap < -0.2 and campaign.get("status") == "running":
        return {"level": "info", "label": "消耗偏慢", "reason": "可放宽出价或扩展受众提高拿量"}
    return {"level": "neutral", "label": "保持观察", "reason": "预算节奏和成本暂未触发自动干预"}


async def _enrich_campaigns(
    campaigns: list[dict],
    project: dict,
    metric_repo: MetricRepository,
) -> list[dict]:
    snapshot = _budget_snapshot(project, campaigns)
    enriched = []

    for campaign in campaigns:
        latest_metric = await metric_repo.get_latest(campaign["id"])
        if latest_metric:
            campaign["installs"] = latest_metric.get("installs")
            campaign["cpi"] = latest_metric.get("cpi")
            campaign["roi"] = latest_metric.get("roi")
            campaign["ctr"] = latest_metric.get("ctr")
            campaign["cvr"] = latest_metric.get("cvr")
            campaign["last_spend"] = latest_metric.get("spend")
            campaign["last_revenue"] = latest_metric.get("revenue")

        campaign["project_name"] = project["name"]
        campaign["budget_type"] = (campaign.get("config") or {}).get("budget_type", "total")
        campaign["budget_remaining"] = max(float(campaign.get("budget") or 0) - float(campaign.get("spent") or 0), 0)
        campaign["budget_usage_rate"] = (
            float(campaign.get("spent") or 0) / float(campaign.get("budget") or 0)
            if float(campaign.get("budget") or 0)
            else 0
        )
        campaign["elapsed_rate"] = _campaign_elapsed_days(campaign) / _campaign_duration_days(campaign)
        campaign["pacing_status"] = (
            "fast" if campaign["budget_usage_rate"] - campaign["elapsed_rate"] > 0.2
            else "slow" if campaign["elapsed_rate"] - campaign["budget_usage_rate"] > 0.2
            else "normal"
        )
        campaign["project_budget"] = snapshot
        campaign["agent_action"] = _agent_action(campaign, snapshot)
        enriched.append(campaign)

    return enriched


async def _get_authorized_campaign_project(
    campaign_id: str,
    current_user: dict,
    campaign_repo: CampaignRepository,
    project_repo: ProjectRepository,
) -> tuple[dict, dict]:
    campaign = await campaign_repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    project = await project_repo.get_by_id(campaign["project_id"])
    if not project or project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    return campaign, project


@router.get("")
async def list_campaigns(
    project_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    metric_repo: MetricRepository = Depends(get_metric_repo),
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
        campaigns = await _enrich_campaigns(campaigns, project, metric_repo)
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
            campaigns.extend(await _enrich_campaigns(project_campaigns, project, metric_repo))
    
    return {"campaigns": campaigns}


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    metric_repo: MetricRepository = Depends(get_metric_repo),
):
    """获取广告投放详情"""
    campaign = await campaign_repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # 验证权限
    project = await project_repo.get_by_id(campaign["project_id"])
    if not project or project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    campaign = (await _enrich_campaigns([campaign], project, metric_repo))[0]
    
    return campaign


@router.post("")
async def create_campaign(
    request: CreateCampaignRequest,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    material_repo: MaterialRepository = Depends(get_material_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    session: AsyncSession = Depends(get_db),
):
    """创建新广告投放"""
    # 验证项目权限
    project = await project_repo.get_by_id(request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    project_campaigns = await campaign_repo.list_by_project(project_id=request.project_id, limit=1000)
    allocated_budget = sum(float(c.get("budget") or 0) for c in project_campaigns)
    project_total_budget = float(project.get("total_budget") or 0)
    if request.budget <= 0:
        raise HTTPException(status_code=422, detail="Budget must be greater than 0")
    if allocated_budget + request.budget > project_total_budget:
        available = max(project_total_budget - allocated_budget, 0)
        raise HTTPException(
            status_code=422,
            detail=f"计划预算超出项目未分配预算，可用额度为 {available:.2f}",
        )

    selected_account = None
    if request.platform_account_id:
        account_result = await session.execute(
            select(PlatformAccount).where(
                PlatformAccount.id == request.platform_account_id,
                PlatformAccount.user_id == current_user["id"],
            )
        )
        selected_account = account_result.scalar_one_or_none()
        if not selected_account:
            raise HTTPException(status_code=404, detail="Platform account not found")

    config = {
        "objective": request.objective,
        "budget_type": request.budget_type or "total",
        "platform_account_id": request.platform_account_id,
        "bidding_strategy": request.bidding_strategy,
        "targeting": {
            "regions": request.target_regions or [],
            "age_range": request.age_range or {},
            "gender": request.gender or "all",
            "interests": request.target_interests or [],
        },
    }
    
    campaign = await campaign_repo.create(
        project_id=request.project_id,
        name=request.name,
        platform=request.platform,
        budget=request.budget,
        platform_account_id=request.platform_account_id,
        objective=request.objective,
        budget_type=request.budget_type or "total",
        daily_budget=request.budget if request.budget_type == "daily" else None,
        lifetime_budget=request.budget if request.budget_type != "daily" else None,
        bid_strategy=request.bidding_strategy,
        status=request.status or "draft",
        target_cpa=request.target_cpa,
        pipeline_step="draft",
        learning_phase="not_started",
        auto_optimize_enabled=request.auto_optimize_enabled if request.auto_optimize_enabled is not None else True,
        optimization_rules=[
            "cpi_guardrail",
            "budget_pacing",
            "creative_fatigue_watch",
        ],
        material_ids=request.material_ids or [],
        start_date=request.start_date,
        end_date=request.end_date,
        config=config,
    )

    if selected_account:
        link_result = await session.execute(
            select(ProjectPlatformAccount).where(
                ProjectPlatformAccount.project_id == request.project_id,
                ProjectPlatformAccount.platform_account_id == request.platform_account_id,
            )
        )
        if not link_result.scalar_one_or_none():
            session.add(ProjectPlatformAccount(
                project_id=request.project_id,
                platform_account_id=request.platform_account_id,
                role="primary",
                status="active",
                note="Auto-linked when creating a campaign",
            ))

    for material_id in request.material_ids or []:
        material = await material_repo.get_by_id(material_id)
        if material and material["user_id"] == current_user["id"]:
            await material_repo.add_to_project(material_id, request.project_id)
            await material_repo.add_to_campaign(material_id, campaign["id"])
    
    # 提交事务以确保数据持久化
    await session.commit()
    
    return campaign


@router.post("/{campaign_id}/metrics")
async def create_campaign_metric(
    campaign_id: str,
    request: MetricCreateRequest,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    session: AsyncSession = Depends(get_db),
):
    """上传一条 Campaign 投放结果数据，用于客户交付后的复盘演示。"""
    campaign = await campaign_repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    project = await project_repo.get_by_id(campaign["project_id"])
    if not project or project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    clicks = int(request.clicks or 0)
    impressions = int(request.impressions or 0)
    installs = int(request.installs or 0)
    conversions = int(request.conversions or 0)
    spend = float(request.spend or 0)
    revenue = float(request.revenue or 0)
    timestamp = datetime.fromisoformat(request.timestamp) if request.timestamp else datetime.utcnow()
    budget = float(campaign.get("budget") or 0)
    if budget and spend > budget:
        raise HTTPException(
            status_code=422,
            detail=f"投放消耗不能超过计划预算，当前计划预算为 {budget:.2f}",
        )

    metric = Metric(
        campaign_id=campaign_id,
        timestamp=timestamp,
        platform=campaign["platform"],
        impressions=impressions,
        clicks=clicks,
        conversions=conversions,
        installs=installs,
        spend=spend,
        revenue=revenue,
        ctr=request.ctr if request.ctr is not None else (clicks / impressions * 100 if impressions else 0),
        cvr=request.cvr if request.cvr is not None else (conversions / clicks * 100 if clicks else 0),
        cpa=request.cpa if request.cpa is not None else (spend / conversions if conversions else 0),
        cpi=request.cpi if request.cpi is not None else (spend / installs if installs else 0),
        roi=request.roi if request.roi is not None else (revenue / spend if spend else 0),
    )
    session.add(metric)
    await campaign_repo.update(campaign_id, spent=spend)
    await session.commit()
    return {
        "id": metric.id,
        "campaign_id": metric.campaign_id,
        "timestamp": metric.timestamp.isoformat(),
        "platform": metric.platform,
        "impressions": metric.impressions,
        "clicks": metric.clicks,
        "conversions": metric.conversions,
        "installs": metric.installs,
        "spend": metric.spend,
        "revenue": metric.revenue,
        "ctr": metric.ctr,
        "cvr": metric.cvr,
        "cpa": metric.cpa,
        "cpi": metric.cpi,
        "roi": metric.roi,
    }


@router.put("/{campaign_id}/status")
async def update_campaign_status(
    campaign_id: str,
    request: UpdateStatusRequest,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    session: AsyncSession = Depends(get_db),
):
    """更新广告投放状态"""
    campaign = await campaign_repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # 验证权限
    project = await project_repo.get_by_id(campaign["project_id"])
    if not project or project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    await campaign_repo.update_status(campaign_id, request.status)
    await session.commit()  # 提交事务到数据库
    return {"message": "Campaign status updated successfully"}


@router.get("/{campaign_id}/materials")
async def get_campaign_materials(
    campaign_id: str,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    campaign_material_repo: CampaignMaterialRepository = Depends(get_campaign_material_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """获取广告投放的素材列表"""
    await _get_authorized_campaign_project(campaign_id, current_user, campaign_repo, project_repo)
    bindings = await campaign_material_repo.list_by_campaign(campaign_id)
    if bindings:
        return {"materials": bindings}

    materials = await campaign_repo.get_materials(campaign_id)
    return {"materials": [{**material, "binding_id": None, "title": None, "description": None, "copy": None} for material in materials]}


@router.post("/{campaign_id}/materials")
async def create_campaign_material_binding(
    campaign_id: str,
    request: CampaignMaterialCreate,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    campaign_material_repo: CampaignMaterialRepository = Depends(get_campaign_material_repo),
    material_repo: MaterialRepository = Depends(get_material_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    session: AsyncSession = Depends(get_db),
):
    """添加或更新计划素材绑定元数据。"""
    campaign, project = await _get_authorized_campaign_project(campaign_id, current_user, campaign_repo, project_repo)

    material = await material_repo.get_by_id(request.material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    if material["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    binding = await campaign_material_repo.create_or_update(
        campaign_id=campaign_id,
        material_id=request.material_id,
        created_by=current_user["id"],
        title=request.title,
        description=request.description,
        copy=request.ad_copy,
        source=request.source,
        sort_order=request.sort_order,
        status=request.status,
    )
    await campaign_repo.add_material(campaign_id, request.material_id)
    await material_repo.add_to_project(request.material_id, project["id"])
    await material_repo.add_to_campaign(request.material_id, campaign["id"])
    await session.commit()
    return binding


@router.put("/{campaign_id}/materials/{binding_id}")
async def update_campaign_material_binding(
    campaign_id: str,
    binding_id: str,
    request: CampaignMaterialUpdate,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    campaign_material_repo: CampaignMaterialRepository = Depends(get_campaign_material_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    session: AsyncSession = Depends(get_db),
):
    """更新计划素材绑定元数据。"""
    await _get_authorized_campaign_project(campaign_id, current_user, campaign_repo, project_repo)
    binding = await campaign_material_repo.update(
        binding_id,
        **request.model_dump(exclude_unset=True),
    )
    if not binding or binding["campaign_id"] != campaign_id:
        raise HTTPException(status_code=404, detail="Campaign material binding not found")
    await session.commit()
    return binding


@router.post("/{campaign_id}/materials/{material_id}")
async def add_material_to_campaign(
    campaign_id: str,
    material_id: str,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    material_repo: MaterialRepository = Depends(get_material_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    campaign_material_repo: CampaignMaterialRepository = Depends(get_campaign_material_repo),
    session: AsyncSession = Depends(get_db),
):
    """添加素材到广告投放"""
    campaign = await campaign_repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # 验证权限
    project = await project_repo.get_by_id(campaign["project_id"])
    if not project or project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    material = await material_repo.get_by_id(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    if material["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    await campaign_repo.add_material(campaign_id, material_id)
    await campaign_material_repo.create_or_update(
        campaign_id=campaign_id,
        material_id=material_id,
        created_by=current_user["id"],
        source="manual",
        status="draft",
    )
    await material_repo.add_to_campaign(material_id, campaign_id)
    await session.commit()
    return {"message": "Material added to campaign successfully"}


@router.delete("/{campaign_id}/materials/{material_id}")
async def remove_material_from_campaign(
    campaign_id: str,
    material_id: str,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    campaign_material_repo: CampaignMaterialRepository = Depends(get_campaign_material_repo),
    material_repo: MaterialRepository = Depends(get_material_repo),
    project_repo: ProjectRepository = Depends(get_project_repo),
    session: AsyncSession = Depends(get_db),
):
    """从广告投放移除素材。参数兼容 binding_id 和旧 material_id。"""
    await _get_authorized_campaign_project(campaign_id, current_user, campaign_repo, project_repo)

    bindings = await campaign_material_repo.list_by_campaign(campaign_id)
    matched = next(
        (
            binding for binding in bindings
            if binding["id"] == material_id or binding["material_id"] == material_id
        ),
        None,
    )
    legacy_material_id = matched["material_id"] if matched else material_id
    if matched:
        await campaign_material_repo.delete(matched["id"])

    await campaign_repo.remove_material(campaign_id, legacy_material_id)
    await material_repo.remove_from_campaign(legacy_material_id, campaign_id)
    await session.commit()
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
