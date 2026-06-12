"""
Agent Task API Routes

遵循 Block 0 规范：
- API 层只负责路由、参数绑定、响应序列化
- 业务逻辑在 Service 层
- user_id 从 get_current_user 获取
- 错误统一处理
"""

import json
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from loguru import logger

from ....api.deps import get_current_user
from ....services.agent_task_service import AgentTaskService
from ....agent_platform.repositories.sqlite import SQLiteAgentTaskRepository
from ....agent_platform.adapters.openai_adapter import OpenAISDKAdapter
from ....agent_platform.runtime import AgentRuntime
from ....agent_platform.errors import AppError, get_http_status
from ....agent_platform.models import AgentTaskStatus
from ....config.settings import get_settings

from .schemas import (
    CreateTaskRequest,
    TaskResponse,
    TaskListResponse,
    EventResponse,
    EventListResponse,
    AgentChatSessionCreateRequest,
    AgentChatSessionResponse,
    AgentChatSessionDetailResponse,
    AgentChatMessageResponse,
)

router = APIRouter(prefix="/agent", tags=["Agent"])

# 全局实例（TODO: 改为依赖注入）
_repo = SQLiteAgentTaskRepository(
    db_path=getattr(_settings, "AGENT_TASK_DB", "runtime/agent/tasks.db")
)
_settings = get_settings()

# 初始化 SDK Adapter
_adapter = OpenAISDKAdapter(
    model=getattr(_settings, "OPENAI_AGENTS_MODEL", "gpt-4o-mini"),
    api_key=_settings.OPENAI_API_KEY,
    base_url=getattr(_settings, "OPENAI_BASE_URL", None),
    enable_tracing=getattr(_settings, "AGENT_TRACING_ENABLED", True),
)

# 初始化 Runtime
_runtime = AgentRuntime(
    adapter=_adapter,
    repo=_repo,
    session_db_path=getattr(_settings, "AGENT_SESSION_DB", "runtime/agent/sessions.db"),
    enable_tracing=getattr(_settings, "AGENT_TRACING_ENABLED", True),
)


def get_agent_task_service() -> AgentTaskService:
    """获取 AgentTaskService 实例"""
    return AgentTaskService(_repo, _runtime)


@router.get("/health")
async def agent_health():
    """Agent 兼容层健康检查（供前端模型列表使用）"""
    return {
        "status": "ok",
        "provider": "openai-compatible",
        "model": getattr(_settings, "OPENAI_AGENTS_MODEL", "gpt-4o-mini"),
        "streaming": True,
    }


# ============ Task API（新版统一接口）============

@router.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(
    req: CreateTaskRequest,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_agent_task_service),
):
    """创建任务"""
    task = await service.create_task(
        user_id=user["id"],
        task_type=req.task_type,
        title=req.title,
        input_data=req.input,
        session_id=req.session_id,
    )
    return TaskResponse(**task.dict())


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_agent_task_service),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    task_type: Optional[str] = Query(None),
    status: Optional[AgentTaskStatus] = Query(None),
):
    """查询任务列表"""
    tasks, total = await service.list_tasks(
        user_id=user["id"],
        limit=limit,
        offset=offset,
        task_type=task_type,
        status=status,
    )
    return TaskListResponse(
        tasks=[TaskResponse(**t.dict()) for t in tasks],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_agent_task_service),
):
    """获取任务详情"""
    task = await service.get_task(user["id"], task_id)
    return TaskResponse(**task.dict())


@router.get("/tasks/{task_id}/events", response_model=EventListResponse)
async def get_task_events(
    task_id: str,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_agent_task_service),
    after_sequence: Optional[int] = Query(None, description="只返回序号大于此值的事件"),
):
    """查询任务事件"""
    events = await service.list_task_events(
        user_id=user["id"],
        task_id=task_id,
        after_sequence=after_sequence,
    )
    return EventListResponse(
        events=[EventResponse(**e.dict()) for e in events],
        task_id=task_id,
        total=len(events),
    )


@router.get("/tasks/{task_id}/stream")
async def stream_task_events(
    task_id: str,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_agent_task_service),
    after_sequence: Optional[int] = Query(None, description="从此序号之后开始推送"),
    request: Request = None,
):
    """
    流式推送任务事件（SSE）
    
    支持断点续传：
    - 前端可通过 after_sequence 参数指定从哪个序号开始
    - 或通过 Last-Event-ID header
    """
    # 优先从 header 获取 last_event_id
    last_event_id = request.headers.get("Last-Event-ID")
    if last_event_id and after_sequence is None:
        try:
            after_sequence = int(last_event_id)
        except ValueError:
            pass
    
    async def event_generator():
        """SSE 事件生成器"""
        try:
            async for event in service.stream_task_events(
                user_id=user["id"],
                task_id=task_id,
                after_sequence=after_sequence,
            ):
                # SSE 格式
                yield f"id: {event.sequence}\n"
                yield f"event: {event.event_type}\n"
                yield f"data: {json.dumps(event.dict(), default=str, ensure_ascii=False)}\n\n"
        except AppError as e:
            # 推送错误事件
            yield f"event: error\n"
            yield f"data: {json.dumps(e.to_dict(), ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/tasks/{task_id}/cancel", status_code=204)
async def cancel_task(
    task_id: str,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_agent_task_service),
):
    """取消任务"""
    await service.cancel_task(user["id"], task_id)
    return None


# ============ 兼容层 API（当前前端接口）============

@router.post("/chat/sessions", response_model=AgentChatSessionResponse, status_code=201)
async def create_chat_session(
    req: AgentChatSessionCreateRequest,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_agent_task_service),
):
    """创建对话（内部创建 conversation Task）"""
    task = await service.create_task(
        user_id=user["id"],
        task_type="conversation",
        title=req.title or "新对话",
    )
    
    # 返回兼容格式
    return AgentChatSessionResponse(
        id=task.task_id,
        title=task.title,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.get("/chat/sessions", response_model=list[AgentChatSessionResponse])
async def list_chat_sessions(
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_agent_task_service),
):
    """查询对话列表"""
    tasks, _ = await service.list_tasks(
        user_id=user["id"],
        task_type="conversation",
        limit=100,
    )
    
    return [
        AgentChatSessionResponse(
            id=task.task_id,
            title=task.title,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
        for task in tasks
    ]


@router.get("/chat/sessions/{session_id}", response_model=AgentChatSessionDetailResponse)
async def get_chat_session(
    session_id: str,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_agent_task_service),
):
    """查询对话详情（内部查询 Task + events）"""
    task = await service.get_task(user["id"], session_id)
    events = await service.list_task_events(user["id"], session_id)
    
    # 转换为前端期望的 messages 格式
    messages = _convert_events_to_messages(events)
    
    return AgentChatSessionDetailResponse(
        session=AgentChatSessionResponse(
            id=task.task_id,
            title=task.title,
            created_at=task.created_at,
            updated_at=task.updated_at,
        ),
        messages=messages,
    )


@router.post("/chat/sessions/{session_id}/stream")
async def stream_chat(
    session_id: str,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_agent_task_service),
    request: Request = None,
):
    """
    流式对话（内部运行 Task）
    
    实现：
    1. 从 request body 获取用户消息
    2. 调用 Runtime 执行任务
    3. 流式推送事件
    """
    # 解析请求体
    body = await request.json()
    user_input = body.get("message", "")
    
    if not user_input:
        async def error_generator():
            yield f"event: error\n"
            yield f"data: {{\"message\": \"Message is required\"}}\n\n"
        return StreamingResponse(
            error_generator(),
            media_type="text/event-stream",
        )
    
    async def event_generator():
        """SSE 事件生成器"""
        try:
            # 运行任务
            async for event in service.run_task(
                user_id=user["id"],
                task_id=session_id,
                user_input=user_input,
            ):
                # SSE 格式
                yield f"id: {event.sequence}\n"
                yield f"event: {event.event_type}\n"
                yield f"data: {json.dumps(event.dict(), default=str, ensure_ascii=False)}\n\n"
        except AppError as e:
            # 推送错误事件
            yield f"event: error\n"
            yield f"data: {json.dumps(e.to_dict(), ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception(f"Unexpected error in stream_chat: {e}")
            yield f"event: error\n"
            yield f"data: {{\"message\": \"An unexpected error occurred\"}}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _convert_events_to_messages(events: list) -> list[AgentChatMessageResponse]:
    """
    将事件流转换为前端期望的消息列表
    
    TODO: 根据实际事件类型完善转换逻辑
    """
    messages = []
    
    # 简单实现：只提取 message.completed 事件
    for event in events:
        if event.event_type == "message.completed":
            payload = event.payload
            messages.append(AgentChatMessageResponse(
                id=payload.get("id", event.event_id),
                role=payload.get("role", "assistant"),
                content=payload.get("content", ""),
                created_at=event.created_at,
                provider=payload.get("provider"),
                model=payload.get("model"),
            ))
    
    return messages
