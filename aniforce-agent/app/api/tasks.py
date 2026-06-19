"""Task 管理 API"""

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.services.agent_task_service import AgentTaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_service() -> AgentTaskService:
    from app.main import _service
    return _service


@router.get("")
async def list_tasks(
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_service),
):
    """列出用户的任务"""
    tasks, total = await service.list_tasks(user_id=user["id"], limit=20)
    return {
        "tasks": [
            {
                "task_id": t.task_id,
                "title": t.title,
                "status": t.status,
                "task_type": t.task_type,
                "session_id": t.session_id,
                "created_at": t.created_at,
            }
            for t in tasks
        ],
        "total": total,
    }


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_service),
):
    """获取任务详情"""
    task = await service.get_task(user["id"], task_id)
    return {
        "task_id": task.task_id,
        "title": task.title,
        "status": task.status,
        "input": task.input,
        "session_id": task.session_id,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_service),
):
    """取消任务"""
    await service.cancel_task(user["id"], task_id)
    return {"status": "cancelled"}