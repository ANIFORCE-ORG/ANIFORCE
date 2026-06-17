"""
Task 管理 API 端点

提供任务管理接口：
- POST /tasks - 创建任务
- GET /tasks - 列出任务
- GET /tasks/{task_id} - 获取任务详情
- GET /tasks/{task_id}/events - 获取事件流
- DELETE /tasks/{task_id} - 取消任务
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from app.api.deps import get_current_user_id
from app.services.task_service import TaskService
from app.repositories.task_repo import TaskRepository
from app.repositories.event_repo import EventRepository
from app.repositories.output_repo import OutputRepository
from app.models.output import OutputStatus
from app.agent.runtime import AgentRuntime
from app.config.database import get_task_db

router = APIRouter(prefix="/tasks", tags=["tasks"])

logger = logging.getLogger(__name__)


class CreateTaskRequest(BaseModel):
    """创建任务请求"""
    task_type: str
    title: str
    input_data: Optional[dict] = None
    session_id: Optional[str] = None


class UpdateOutputStatusRequest(BaseModel):
    """更新 Output 状态请求"""
    status: str


async def get_task_service(db=Depends(get_task_db)) -> TaskService:
    """获取 TaskService 实例"""
    task_repo = TaskRepository(db)
    event_repo = EventRepository(db)
    agent_runtime = AgentRuntime()
    return TaskService(
        task_repo=task_repo,
        event_repo=event_repo,
        agent_runtime=agent_runtime,
    )


@router.post("")
async def create_task(
    request: CreateTaskRequest,
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service),
):
    """创建任务"""
    task = await task_service.create_task(
        user_id=user_id,
        task_type=request.task_type,
        title=request.title,
        input_data=request.input_data,
        session_id=request.session_id,
    )
    return {
        "task_id": task.task_id,
        "status": task.status.value,
        "title": task.title,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@router.get("")
async def list_tasks(
    task_type: Optional[str] = None,
    limit: int = 50,
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service),
):
    """列出用户任务"""
    tasks = await task_service.list_tasks(user_id, task_type, limit)
    return {
        "tasks": [
            {
                "task_id": task.task_id,
                "task_type": task.task_type,
                "status": task.status.value,
                "title": task.title,
                "session_id": task.session_id,
                "created_at": task.created_at.isoformat() if task.created_at else None,
            }
            for task in tasks
        ]
    }


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service),
):
    """获取任务详情"""
    task = await task_service.get_task(task_id, user_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "task_id": task.task_id,
        "task_type": task.task_type,
        "status": task.status.value,
        "title": task.title,
        "session_id": task.session_id,
        "input_data": task.input_data,
        "result": task.result,
        "error": task.error,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


@router.get("/{task_id}/outputs")
async def get_task_outputs(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service),
    db=Depends(get_task_db),
):
    """获取任务产物"""
    task = await task_service.get_task(task_id, user_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    output_repo = OutputRepository(db)
    outputs = await output_repo.list_by_task(task_id)
    return {"outputs": [output.to_dict() for output in outputs]}


@router.get("/{task_id}/events")
async def get_task_events(
    task_id: str,
    after_sequence: Optional[int] = None,
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service),
):
    """获取任务事件流（断点续传）"""
    events = await task_service.get_task_events(task_id, user_id, after_sequence)

    return {
        "events": [
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "payload": event.payload,
                "sequence": event.sequence,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in events
        ]
    }


@router.patch("/outputs/{output_id}")
async def update_output_status(
    output_id: str,
    request: UpdateOutputStatusRequest,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_task_db),
):
    """验证/拒绝任务产物"""
    output_repo = OutputRepository(db)
    output = await output_repo.get_by_id(output_id)
    if not output:
        raise HTTPException(status_code=404, detail="Output not found")

    # 验证产物属于该用户的任务
    task_repo = TaskRepository(db)
    task = await task_repo.get_by_id(output.task_id, user_id)
    if not task:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        output_status = OutputStatus(request.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")

    success = await output_repo.update_status(
        output_id, output_status, verified_by=user_id if output_status == OutputStatus.VERIFIED else None
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update status")

    return {"output_id": output_id, "status": request.status}


@router.delete("/{task_id}")
async def cancel_task(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service),
):
    """取消任务"""
    await task_service.cancel_task(task_id, user_id)
    return {"message": "Task cancelled", "task_id": task_id}
