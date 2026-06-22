"""项目管理 API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.repositories.protocols import ProjectRepository
from app.repositories.factory import get_project_repo
from app.api.deps import get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    """创建项目请求模型（同时创建初始Campaign）"""
    # Project 字段
    name: str
    product: str | None = None
    total_budget: float
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    
    # Campaign 字段
    channel: str  # 投放渠道: Meta, Google, TikTok
    account: str  # 广告账户ID
    countries: str | None = None
    campaignName: str  # Campaign名称
    objective: str | None = None
    buyingType: str | None = None
    specialAdCategories: str | None = None
    abTest: str | None = None
    campaignBudget: str | None = None
    campaignStatus: str | None = "Draft"
    budgetType: str | None = None
    budget: str | None = None
    bidStrategy: str | None = None
    spendLimit: str | None = None
    start: str | None = None  # Campaign开始时间
    end: str | None = None    # Campaign结束时间
    
    # 旧字段（保持兼容）
    game_type: str | None = None
    target_market: str | None = None
    tags: list[str] | None = None
    manager: str | None = None


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


@router.post("")
async def create_project(
    request: CreateProjectRequest,
    current_user: dict = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """创建新项目（同时创建初始Campaign）"""
    from app.models.campaign import Campaign, Platform, CampaignStatus
    from datetime import datetime
    import uuid
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # 1. 创建 Project
        logger.info(f"Creating project: {request.name} for user: {current_user['id']}")
        project = await project_repo.create(
            user_id=current_user["id"],
            name=request.name,
            product=request.product,
            total_budget=request.total_budget,
            description=request.description,
            game_type=request.game_type,
            target_market=request.target_market,
            tags=request.tags,
            manager=request.manager,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        logger.info(f"Project created with ID: {project['id']}")
        
        # 2. 解析 Platform 枚举
        try:
            # Platform 枚举值是首字母大写的，如 "Meta", "Google", "TikTok"
            platform = Platform[request.channel]
        except KeyError:
            logger.error(f"Invalid platform: {request.channel}")
            raise HTTPException(status_code=400, detail=f"Invalid platform: {request.channel}. Valid values: Meta, Google, TikTok")
        
        # 3. 解析 CampaignStatus 枚举
        # CampaignStatus 枚举值是小写的，如 "draft", "running", "paused"
        # 前端发送的是首字母大写的，如 "Draft", "Running", "Paused"
        try:
            if request.campaignStatus:
                status = CampaignStatus[request.campaignStatus.upper()]
            else:
                status = CampaignStatus.DRAFT
        except KeyError:
            logger.warning(f"Invalid campaign status: {request.campaignStatus}, using DRAFT")
            status = CampaignStatus.DRAFT
        
        # 4. 处理日期
        campaign_start_date = None
        campaign_end_date = None
        
        if request.start:
            try:
                campaign_start_date = datetime.fromisoformat(request.start).date()
            except (ValueError, AttributeError):
                campaign_start_date = None
        elif request.start_date:
            try:
                campaign_start_date = datetime.fromisoformat(request.start_date).date()
            except (ValueError, AttributeError):
                campaign_start_date = None
        
        if request.end:
            try:
                campaign_end_date = datetime.fromisoformat(request.end).date()
            except (ValueError, AttributeError):
                campaign_end_date = None
        elif request.end_date:
            try:
                campaign_end_date = datetime.fromisoformat(request.end_date).date()
            except (ValueError, AttributeError):
                campaign_end_date = None
        
        # 5. 创建初始 Campaign
        logger.info(f"Creating campaign: {request.campaignName} for project: {project['id']}")
        campaign = Campaign(
            id=str(uuid.uuid4()),
            project_id=project["id"],
            name=request.campaignName,
            platform=platform,
            account_id=request.account,
            countries=request.countries,
            platform_campaign_id=None,  # 创建后由平台API返回并更新
            objective=request.objective,
            buying_type=request.buyingType,
            special_ad_categories=request.specialAdCategories,
            ab_test=request.abTest,
            campaign_budget_optimization=request.campaignBudget,
            budget_type=request.budgetType,
            budget=float(request.budget) if request.budget else 0.0,
            bid_strategy=request.bidStrategy,
            spend_limit=float(request.spendLimit) if request.spendLimit else None,
            status=status,
            start_date=campaign_start_date,
            end_date=campaign_end_date,
            spent=0.0,
        )
        
        project_repo.session.add(campaign)
        
        # 提交事务以确保数据持久化
        await project_repo.session.commit()
        logger.info(f"Campaign created with ID: {campaign.id}")
        
        return project
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create project: {str(e)}", exc_info=True)
        await project_repo.session.rollback()
        raise HTTPException(status_code=500, detail=f"创建项目失败: {str(e)}")


@router.put("/{project_id}")
async def update_project(
    project_id: str,
    name: str | None = None,
    total_budget: float | None = None,
    status: str | None = None,
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
    if name is not None:
        update_data["name"] = name
    if total_budget is not None:
        update_data["total_budget"] = total_budget
    if status is not None:
        update_data["status"] = status
    
    await project_repo.update(project_id, **update_data)
    return {"message": "Project updated successfully"}


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
