"""Agent Run API 端点"""

import logging
import uuid
from typing import Any, Optional

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.runtime import AgentRuntime
from app.api.deps import get_current_user_id
from app.config.database import get_task_db
from app.config.settings import get_settings
from app.repositories.event_repo import EventRepository
from app.repositories.task_repo import TaskRepository
from app.services.business_event_adapter import BusinessEventAdapter
from app.services.task_service import TaskService

router = APIRouter(prefix="/runs", tags=["agent-runs"])
logger = logging.getLogger(__name__)


class RunRequest(BaseModel):
    """Agent 运行请求"""

    prompt: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    task_type: str = "conversation"
    title: Optional[str] = None
    model: Optional[str] = None
    max_turns: int = 20
    include_raw_events: bool = False
    input_data: Optional[dict[str, Any]] = None
    allowed_tools: Optional[list[str]] = None  # 允许的工具列表


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
async def run_agent(
    request: RunRequest,
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service),
):
    """运行 Agent 并返回 ANIFORCE 业务事件 SSE"""
    session_id = request.session_id or str(uuid.uuid4())
    try:
        uuid.UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="session_id must be a UUID") from exc

    input_data = dict(request.input_data or {})
    input_data.update(
        {
            "prompt": request.prompt,
            "model": request.model,
            "max_turns": request.max_turns,
        }
    )

    task = await task_service.create_task(
        user_id=user_id,
        task_type=request.task_type,
        title=request.title or request.prompt[:50],
        input_data=input_data,
        session_id=session_id,
    )

    logger.info(
        "Agent run started: task_id=%s session_id=%s user_id=%s task_type=%s",
        task.task_id,
        session_id,
        user_id,
        request.task_type,
    )

    async def event_generator():
        async with aiosqlite.connect(get_settings().TASK_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            sdk_messages = task_service.run_task(
                task_id=task.task_id,
                user_id=user_id,
                prompt=request.prompt,
                session_id=session_id,
                model=request.model,
                max_turns=request.max_turns,
                allowed_tools=request.allowed_tools,
            )
            async for sse_event in BusinessEventAdapter.stream_business_events(
                task_id=task.task_id,
                user_id=user_id,
                task_type=request.task_type,
                prompt=request.prompt,
                session_id=session_id,
                sdk_messages=sdk_messages,
                db=db,
                include_raw_events=request.include_raw_events,
            ):
                yield sse_event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
