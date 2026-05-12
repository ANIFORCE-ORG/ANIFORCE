"""项目管理 API"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.config.database import get_db
from app.models import AgentAction, Campaign, Metric, PlatformAccount, ProjectPlatformAccount
from app.repositories.protocols import CampaignMaterialRepository, CampaignRepository, MaterialRepository, MetricRepository, ProjectRepository
from app.repositories.factory import get_campaign_material_repo, get_campaign_repo, get_material_repo, get_metric_repo, get_project_repo
from app.api.deps import get_current_user
from app.schemas.campaign_material import BatchCampaignCreateRequest

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    """创建项目请求模型"""
    name: str
    total_budget: float
    description: str | None = None
    game_type: str | None = None
    target_market: str | None = None
    tags: list[str] | None = None
    manager: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class ProjectPlatformAccountRequest(BaseModel):
    platform_account_id: str
    role: str | None = "primary"
    spend_cap: float | None = None
    daily_cap: float | None = None
    note: str | None = None


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    game_type: str | None = None
    target_market: str | None = None
    total_budget: float | None = None
    status: str | None = None
    product_type: str | None = None
    region: list[str] | None = None
    target_roi: float | None = None
    manager: str | None = None
    start_date: str | None = None
    end_date: str | None = None


def _campaign_config(campaign: Campaign) -> dict:
    if not campaign.config:
        return {}
    if isinstance(campaign.config, dict):
        return campaign.config
    try:
        return json.loads(campaign.config)
    except (TypeError, json.JSONDecodeError):
        return {}


def _campaign_platform_value(campaign: Campaign) -> str:
    return getattr(campaign.platform, "value", campaign.platform)


def _render_plan_name(template: str, index: int) -> str:
    if "{index}" in template:
        return template.replace("{index}", str(index))
    return f"{template}_{index}"


def _platform_value(platform: str) -> str:
    mapping = {
        "meta": "Meta",
        "google": "Google",
        "tiktok": "TikTok",
        "Meta": "Meta",
        "Google": "Google",
        "TikTok": "TikTok",
    }
    return mapping.get(platform, platform)


@router.get("")
async def list_projects(
    status: str | None = None,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """获取用户的项目列表"""
    projects = await project_repo.list_by_user(
        user_id=current_user["id"],
        status=status,
        limit=limit
    )
    return {"projects": projects}


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """获取项目详情"""
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # 验证权限
    if project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    return project


@router.get("/{project_id}/plan-workspace")
async def get_project_plan_workspace(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    metric_repo: MetricRepository = Depends(get_metric_repo),
    campaign_material_repo: CampaignMaterialRepository = Depends(get_campaign_material_repo),
    session: AsyncSession = Depends(get_db),
):
    """项目计划工作台聚合接口。"""
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    campaigns = await campaign_repo.list_by_project(project_id=project_id, limit=1000)
    allocated = sum(float(campaign.get("budget") or 0) for campaign in campaigns)
    total = float(project.get("total_budget") or 0)
    spent = float(project.get("spent") or 0)

    enriched_campaigns = []
    for campaign in campaigns:
        latest_metric = await metric_repo.get_latest(campaign["id"])
        bindings = await campaign_material_repo.list_by_campaign(campaign["id"])
        enriched_campaigns.append({
            **campaign,
            "latest_metric": latest_metric,
            "material_binding_count": len(bindings) if bindings else len(campaign.get("material_ids") or []),
            "materials": bindings,
        })

    account_result = await session.execute(
        select(ProjectPlatformAccount)
        .options(selectinload(ProjectPlatformAccount.account))
        .join(PlatformAccount, ProjectPlatformAccount.platform_account_id == PlatformAccount.id)
        .where(ProjectPlatformAccount.project_id == project_id)
        .order_by(ProjectPlatformAccount.updated_at.desc())
    )
    action_result = await session.execute(
        select(AgentAction)
        .where(AgentAction.project_id == project_id)
        .order_by(AgentAction.created_at.desc())
    )

    return {
        "project": project,
        "platform_accounts": [link.to_dict() for link in account_result.scalars().all()],
        "campaigns": enriched_campaigns,
        "agent_actions": [action.to_dict() for action in action_result.scalars().all()],
        "budget": {
            "total": total,
            "allocated": allocated,
            "unallocated": max(total - allocated, 0),
            "spent": spent,
            "remaining": max(total - spent, 0),
        },
    }


@router.post("/{project_id}/campaigns/batch")
async def batch_create_project_campaigns(
    project_id: str,
    request: BatchCampaignCreateRequest,
    current_user: dict = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
    campaign_material_repo: CampaignMaterialRepository = Depends(get_campaign_material_repo),
    material_repo: MaterialRepository = Depends(get_material_repo),
    session: AsyncSession = Depends(get_db),
):
    """从项目上下文批量创建计划，并写入计划-素材绑定元数据。"""
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    existing_campaigns = await campaign_repo.list_by_project(project_id=project_id, limit=1000)
    allocated_budget = sum(float(campaign.get("budget") or 0) for campaign in existing_campaigns)
    requested_budget = request.plan_count * float(request.budget)
    project_total_budget = float(project.get("total_budget") or 0)
    if allocated_budget + requested_budget > project_total_budget:
        available = max(project_total_budget - allocated_budget, 0)
        raise HTTPException(
            status_code=422,
            detail=f"批量计划预算超出项目未分配预算，可用额度为 {available:.2f}",
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

    materials = []
    for binding in request.materials:
        material = await material_repo.get_by_id(binding.material_id)
        if not material:
            raise HTTPException(status_code=404, detail=f"Material not found: {binding.material_id}")
        if material["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail=f"Permission denied for material: {binding.material_id}")
        materials.append(binding)

    if request.plan_count == 0:
        return {
            "campaigns": [],
            "material_bindings": [],
            "plan_count": 0,
            "skipped": True,
            "message": "Preview only, no campaigns created.",
        }

    if selected_account:
        link_result = await session.execute(
            select(ProjectPlatformAccount).where(
                ProjectPlatformAccount.project_id == project_id,
                ProjectPlatformAccount.platform_account_id == request.platform_account_id,
            )
        )
        if not link_result.scalar_one_or_none():
            session.add(ProjectPlatformAccount(
                project_id=project_id,
                platform_account_id=request.platform_account_id,
                role="primary",
                status="active",
                note="Auto-linked when batch creating campaigns",
            ))

    campaigns = []
    material_bindings = []
    material_ids = [binding.material_id for binding in materials]
    for index in range(1, request.plan_count + 1):
        config = {
            "objective": request.objective,
            "budget_type": request.budget_type,
            "platform_account_id": request.platform_account_id,
            "bidding_strategy": request.bidding_strategy,
            "targeting": request.targeting.model_dump(),
            "batch": {
                "name_template": request.name_template,
                "index": index,
                "plan_count": request.plan_count,
            },
        }
        campaign = await campaign_repo.create(
            project_id=project_id,
            name=_render_plan_name(request.name_template, index),
            platform=_platform_value(request.platform),
            budget=request.budget,
            platform_account_id=request.platform_account_id,
            objective=request.objective,
            budget_type=request.budget_type,
            daily_budget=request.budget if request.budget_type == "daily" else None,
            lifetime_budget=request.budget if request.budget_type != "daily" else None,
            bid_strategy=request.bidding_strategy,
            status=request.status,
            target_cpa=request.target_cpa,
            pipeline_step="draft",
            learning_phase="not_started",
            auto_optimize_enabled=request.auto_optimize_enabled,
            optimization_rules=["cpi_guardrail", "budget_pacing", "creative_fatigue_watch"],
            material_ids=material_ids,
            start_date=request.start_date.isoformat() if request.start_date else None,
            end_date=request.end_date.isoformat() if request.end_date else None,
            config=config,
        )
        campaigns.append(campaign)

        for binding in materials:
            created = await campaign_material_repo.create_or_update(
                campaign_id=campaign["id"],
                material_id=binding.material_id,
                created_by=current_user["id"],
                title=binding.title,
                description=binding.description,
                copy=binding.ad_copy,
                source=binding.source,
                sort_order=binding.sort_order,
                status=binding.status,
            )
            material_bindings.append(created)
            await material_repo.add_to_project(binding.material_id, project_id)
            await material_repo.add_to_campaign(binding.material_id, campaign["id"])

    await session.commit()
    return {
        "campaigns": campaigns,
        "material_bindings": material_bindings,
        "plan_count": len(campaigns),
        "skipped": False,
        "message": "Campaigns created successfully.",
    }


@router.get("/{project_id}/platform-accounts")
async def get_project_platform_accounts(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    session: AsyncSession = Depends(get_db),
):
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    result = await session.execute(
        select(ProjectPlatformAccount)
        .options(selectinload(ProjectPlatformAccount.account))
        .join(PlatformAccount, ProjectPlatformAccount.platform_account_id == PlatformAccount.id)
        .where(ProjectPlatformAccount.project_id == project_id)
        .order_by(ProjectPlatformAccount.updated_at.desc())
    )
    return [link.to_dict() for link in result.scalars().all()]


@router.post("/{project_id}/platform-accounts")
async def bind_project_platform_account(
    project_id: str,
    request: ProjectPlatformAccountRequest,
    current_user: dict = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    session: AsyncSession = Depends(get_db),
):
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    account_result = await session.execute(
        select(PlatformAccount).where(
            PlatformAccount.id == request.platform_account_id,
            PlatformAccount.user_id == current_user["id"],
        )
    )
    account = account_result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Platform account not found")

    result = await session.execute(
        select(ProjectPlatformAccount).where(
            ProjectPlatformAccount.project_id == project_id,
            ProjectPlatformAccount.platform_account_id == account.id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        link = ProjectPlatformAccount(
            project_id=project_id,
            platform_account_id=account.id,
        )
        session.add(link)

    link.role = request.role or "primary"
    link.status = "active"
    link.spend_cap = request.spend_cap
    link.daily_cap = request.daily_cap
    link.note = request.note
    await session.commit()
    await session.refresh(link)
    await session.refresh(link, ["account"])
    return link.to_dict()


@router.delete("/{project_id}/platform-accounts/{platform_account_id}")
async def unbind_project_platform_account(
    project_id: str,
    platform_account_id: str,
    current_user: dict = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    session: AsyncSession = Depends(get_db),
):
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    result = await session.execute(
        select(ProjectPlatformAccount).where(
            ProjectPlatformAccount.project_id == project_id,
            ProjectPlatformAccount.platform_account_id == platform_account_id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Project account binding not found")
    await session.delete(link)
    await session.commit()
    return {"message": "Project account binding removed"}


@router.get("/{project_id}/agent-actions")
async def get_project_agent_actions(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    session: AsyncSession = Depends(get_db),
):
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    result = await session.execute(
        select(AgentAction)
        .where(AgentAction.project_id == project_id)
        .order_by(AgentAction.created_at.desc())
    )
    return [action.to_dict() for action in result.scalars().all()]


@router.post("/{project_id}/agent-actions/generate")
async def generate_project_agent_actions(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    session: AsyncSession = Depends(get_db),
):
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    existing_result = await session.execute(
        select(AgentAction).where(
            AgentAction.project_id == project_id,
            AgentAction.status == "suggested",
        )
    )
    for action in existing_result.scalars().all():
        action.status = "expired"

    created: list[AgentAction] = []
    account_links = (
        await session.execute(
            select(ProjectPlatformAccount).where(ProjectPlatformAccount.project_id == project_id)
        )
    ).scalars().all()
    if not account_links:
        created.append(AgentAction(
            user_id=current_user["id"],
            project_id=project_id,
            action_type="bind_platform_account",
            risk_level="L1",
            status="suggested",
            title="为项目绑定广告账户",
            summary="当前项目没有绑定广告账户，创建真实平台 Campaign 前建议先绑定可用账户。",
            evidence_json=json.dumps({"linked_accounts": 0}),
            payload_json=json.dumps({"target": "project_platform_accounts"}),
            expected_impact_json=json.dumps({"impact": "避免创建广告计划时误选无关账户"}),
        ))

    campaigns = (
        await session.execute(select(Campaign).where(Campaign.project_id == project_id))
    ).scalars().all()
    for campaign in campaigns:
        config = _campaign_config(campaign)
        campaign_platform_account_id = campaign.platform_account_id or config.get("platform_account_id")
        budget = float(campaign.budget or 0)
        spent = float(campaign.spent or 0)
        usage = spent / budget if budget else 0
        if budget and usage >= 0.9:
            created.append(AgentAction(
                user_id=current_user["id"],
                project_id=project_id,
                platform_account_id=campaign_platform_account_id,
                campaign_id=campaign.id,
                action_type="review_budget",
                risk_level="L2",
                status="suggested",
                title=f"检查计划预算：{campaign.name}",
                summary="该计划预算使用率已超过 90%，建议确认是否补预算、降速或暂停。",
                evidence_json=json.dumps({"budget": budget, "spent": spent, "usage_rate": usage}),
                payload_json=json.dumps({"campaign_id": campaign.id}),
                expected_impact_json=json.dumps({"impact": "避免预算耗尽导致投放中断"}),
            ))
        latest_metric_result = await session.execute(
            select(Metric)
            .where(Metric.campaign_id == campaign.id)
            .order_by(Metric.timestamp.desc())
            .limit(1)
        )
        latest_metric = latest_metric_result.scalar_one_or_none()
        target_cpa = float(campaign.target_cpa or 0)
        cpi = float(latest_metric.cpi or 0) if latest_metric else 0
        if target_cpa and cpi and cpi > target_cpa * 1.15:
            created.append(AgentAction(
                user_id=current_user["id"],
                project_id=project_id,
                platform_account_id=campaign_platform_account_id,
                campaign_id=campaign.id,
                action_type="review_cpi",
                risk_level="L2",
                status="suggested",
                title=f"检查计划成本：{campaign.name}",
                summary="该计划最新 CPI 已高于目标 15%，建议收窄定向、降低预算或替换疲劳素材。",
                evidence_json=json.dumps({
                    "campaign_id": campaign.id,
                    "target_cpa": target_cpa,
                    "latest_cpi": cpi,
                }),
                payload_json=json.dumps({"campaign_id": campaign.id}),
                expected_impact_json=json.dumps({"impact": "降低获客成本并减少低效消耗"}),
            ))
        if not campaign_platform_account_id:
            created.append(AgentAction(
                user_id=current_user["id"],
                project_id=project_id,
                campaign_id=campaign.id,
                action_type="link_campaign_account",
                risk_level="L1",
                status="suggested",
                title=f"补充计划广告账户：{campaign.name}",
                summary="该计划没有绑定平台广告账户，后续同步、诊断和执行会缺少真实平台定位。",
                evidence_json=json.dumps({"campaign_id": campaign.id, "platform": _campaign_platform_value(campaign)}),
                payload_json=json.dumps({"campaign_id": campaign.id}),
                expected_impact_json=json.dumps({"impact": "让 Agent 能定位真实平台对象"}),
            ))

    for action in created:
        session.add(action)
    await session.commit()
    return {"actions": [action.to_dict() for action in created]}


@router.post("/{project_id}/agent-actions/{action_id}/confirm")
async def confirm_project_agent_action(
    project_id: str,
    action_id: str,
    current_user: dict = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    session: AsyncSession = Depends(get_db),
):
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    result = await session.execute(
        select(AgentAction).where(AgentAction.id == action_id, AgentAction.project_id == project_id)
    )
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Agent action not found")
    if action.status != "suggested":
        raise HTTPException(status_code=409, detail=f"Agent action is already {action.status}")
    action.status = "confirmed"
    action.confirmed_by = current_user["id"]
    action.confirmed_at = datetime.utcnow()
    await session.commit()
    return action.to_dict()


@router.post("/{project_id}/agent-actions/{action_id}/reject")
async def reject_project_agent_action(
    project_id: str,
    action_id: str,
    current_user: dict = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
    session: AsyncSession = Depends(get_db),
):
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    result = await session.execute(
        select(AgentAction).where(AgentAction.id == action_id, AgentAction.project_id == project_id)
    )
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Agent action not found")
    if action.status != "suggested":
        raise HTTPException(status_code=409, detail=f"Agent action is already {action.status}")
    action.status = "rejected"
    action.confirmed_by = current_user["id"]
    action.confirmed_at = datetime.utcnow()
    await session.commit()
    return action.to_dict()


@router.post("")
async def create_project(
    request: CreateProjectRequest,
    current_user: dict = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """创建新项目"""
    project = await project_repo.create(
        user_id=current_user["id"],
        name=request.name,
        total_budget=request.total_budget,
        description=request.description,
        game_type=request.game_type,
        target_market=request.target_market,
        tags=request.tags,
        manager=request.manager,
        start_date=request.start_date,
        end_date=request.end_date,
    )
    # 提交事务以确保数据持久化
    await project_repo.session.commit()
    return project


@router.put("/{project_id}")
async def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    current_user: dict = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """更新项目"""
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    update_data = {}
    for key, value in request.model_dump(exclude_unset=True).items():
        update_data[key] = value
    
    updated = await project_repo.update(project_id, **update_data)
    return updated or await project_repo.get_by_id(project_id)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """删除项目"""
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    await project_repo.delete(project_id)
    return {"message": "Project deleted successfully"}
