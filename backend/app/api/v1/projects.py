"""项目管理 API"""
from fastapi import APIRouter, Depends, HTTPException
from app.repositories.protocols import ProjectRepository
from app.repositories.factory import get_project_repo
from app.api.deps import get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])


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
    name: str,
    total_budget: float,
    game_type: str | None = None,
    target_market: str | None = None,
    tags: list[str] | None = None,
    manager: str | None = None,
    current_user: dict = Depends(get_current_user),
    project_repo: ProjectRepository = Depends(get_project_repo),
):
    """创建新项目"""
    project = await project_repo.create(
        user_id=current_user["id"],
        name=name,
        total_budget=total_budget,
        game_type=game_type,
        target_market=target_market,
        tags=tags,
        manager=manager,
    )
    return project


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
