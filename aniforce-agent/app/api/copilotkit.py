"""
CopilotKit API 端点

提供 CopilotKit 标准接口：
- GET /copilotkit/info - Agent 信息
- POST /copilotkit/agent/default/run - 运行 Agent（SSE 流式）
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

from app.api.deps import get_current_user_id
from app.services.task_service import TaskService
from app.services.copilotkit_adapter import CopilotKitAdapter, get_copilotkit_info
from app.repositories.task_repo import TaskRepository
from app.repositories.event_repo import EventRepository
from app.agent.runtime import AgentRuntime
from app.config.database import get_task_db

router = APIRouter(prefix="/copilotkit", tags=["copilotkit"])

logger = logging.getLogger(__name__)


class Message(BaseModel):
    """消息模型"""
    role: str
    content: str


class AgentRunRequest(BaseModel):
    """Agent 运行请求"""
    messages: list[Message]
    threadId: Optional[str] = None  # CopilotKit 的 session_id
    state: Optional[Dict[str, Any]] = None


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


@router.get("/info")
async def copilotkit_info():
    """
    返回 Agent 配置信息

    CopilotKit 协议：/info
    """
    return get_copilotkit_info()


@router.post("/agent/default/run")
async def run_agent(
    request: AgentRunRequest,
    user_id: str = Depends(get_current_user_id),
    task_service: TaskService = Depends(get_task_service),
):
    """
    运行 Agent（流式响应）

    CopilotKit 协议：/agent/{agent_name}/run

    Args:
        request: 运行请求（包含消息历史和 threadId）
        user_id: 当前用户 ID
        task_service: 任务服务

    Returns:
        SSE 流式响应
    """
    # 提取最后一条用户消息作为 prompt
    user_messages = [msg for msg in request.messages if msg.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user message found")

    prompt = user_messages[-1].content

    # 使用 threadId 作为 session_id（如果没有则创建新的）
    session_id = request.threadId or f"session_{user_id}_{id(request)}"

    # 创建任务
    task = await task_service.create_task(
        user_id=user_id,
        task_type="conversation",
        title=prompt[:50],  # 用前 50 字符作为标题
        input_data={"prompt": prompt, "messages": [msg.dict() for msg in request.messages]},
        session_id=session_id,
    )

    logger.info(
        f"Agent run started: task_id={task.task_id}, session_id={session_id}, user_id={user_id}"
    )

    # 流式执行任务
    async def event_generator():
        """SSE 事件生成器"""
        try:
            # 运行任务并获取 SDK 消息流
            sdk_messages = task_service.run_task(
                task_id=task.task_id,
                user_id=user_id,
                prompt=prompt,
                session_id=session_id,
            )

            # 转换为 AG-UI 事件流
            async for sse_event in CopilotKitAdapter.stream_ag_ui_events(
                task_id=task.task_id,
                sdk_messages=sdk_messages,
            ):
                yield sse_event

        except Exception as e:
            logger.error(f"Agent run error: {e}", exc_info=True)
            # 发送错误事件
            error_event = CopilotKitAdapter._format_sse(
                {
                    "event": "ERROR",
                    "data": {
                        "runId": task.task_id,
                        "error": str(e),
                    },
                }
            )
            yield error_event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )
