"""项目管理 API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.repositories.protocols import ProjectRepository
from app.repositories.factory import get_project_repo
from app.api.deps import get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    """创建项目请求模型"""
    # Project 字段
    name: str
    product: str | None = None
    target_market: str | None = None
    status: str | None = "active"
    start_date: str | None = None
    end_date: str | None = None
    total_budget: float | None = 0
    manager: str | None = None
    game_type: str | None = None
    tags: list[str] | None = None
    description: str | None = None


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
    """创建新项目"""
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Creating project: {request.name} for user: {current_user['id']}")
        
        project = await project_repo.create(
            user_id=current_user["id"],
            name=request.name,
            product=request.product,
            total_budget=request.total_budget or 0,
            description=request.description,
            game_type=request.game_type,
            target_market=request.target_market,
            tags=request.tags,
            manager=request.manager,
            start_date=request.start_date,
            end_date=request.end_date,
            status=request.status or "active",
        )
        
        logger.info(f"Project created with ID: {project['id']}")
        
        return project
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create project: {str(e)}", exc_info=True)
        await project_repo.session.rollback()
        raise HTTPException(status_code=500, detail=f"创建项目失败: {str(e)}")


class UpdateProjectRequest(BaseModel):
    """更新项目请求模型"""
    name: str | None = None
    product: str | None = None
    target_market: str | None = None
    status: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    total_budget: float | None = None
    description: str | None = None


@router.put("/{project_id}")
async def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    current_user: dict = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """更新项目"""
    import logging
    
    logger = logging.getLogger(__name__)
    
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # 构建更新数据
    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.product is not None:
        update_data["product"] = request.product
    if request.target_market is not None:
        update_data["target_market"] = request.target_market
    if request.status is not None:
        update_data["status"] = request.status
    if request.start_date is not None:
        update_data["start_date"] = request.start_date
    if request.end_date is not None:
        update_data["end_date"] = request.end_date
    if request.total_budget is not None:
        update_data["total_budget"] = request.total_budget
    if request.description is not None:
        update_data["description"] = request.description
    
    logger.info(f"Updating project {project_id} with data: {update_data}")
    
    await project_repo.update(project_id, **update_data)
    
    # 返回更新后的项目
    updated_project = await project_repo.get_by_id(project_id)
    return updated_project


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
