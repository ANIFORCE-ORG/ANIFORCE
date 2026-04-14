"""广告投放管理 API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.protocols import CampaignRepository, ProjectRepository
from app.repositories.factory import get_campaign_repo, get_project_repo
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
    request: CreateCampaignRequest,
    current_user: dict = Depends(get_current_user),
    campaign_repo: CampaignRepository = Depends(get_campaign_repo),
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
    
    campaign = await campaign_repo.create(
        project_id=request.project_id,
        name=request.name,
        platform=request.platform,
        budget=request.budget,
        status=request.status or "draft",
        material_ids=request.material_ids or [],
    )
    
    # 提交事务以确保数据持久化
    await session.commit()
    
    return campaign


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
