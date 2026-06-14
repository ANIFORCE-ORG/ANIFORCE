"""
AG-UI Protocol API Routes

为 CopilotKit @ag-ui/client HttpAgent 提供兼容端点。
端点路径: /api/v1/copilotkit
"""

import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from loguru import logger

from ..deps import get_current_user
from ...services.agent_task_service import AgentTaskService
from ...agent_platform.repositories.sqlite import SQLiteAgentTaskRepository
from ...agent_platform.adapters.openai_adapter import OpenAISDKAdapter
from ...agent_platform.runtime import AgentRuntime
from ...agent_platform.adapters.agui_adapter import (
    AgUiRequest,
    agui_sse_generator,
)
from ...agent_platform.adapters.agui_registry import (
    ToolRegistry,
    create_default_tool_registry,
)
from ...config.settings import get_settings

router = APIRouter(prefix="/copilotkit", tags=["AG-UI"])

# 全局工具注册表 — Skills 或配置可通过 import 注册新工具
_global_tool_registry: ToolRegistry = create_default_tool_registry()


def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册表（Skills 可通过此函数注册工具）"""
    return _global_tool_registry

_settings = get_settings()
_repo = SQLiteAgentTaskRepository(
    db_path=getattr(_settings, "AGENT_TASK_DB", "runtime/agent/tasks.db")
)

_adapter = OpenAISDKAdapter(
    model=getattr(_settings, "OPENAI_AGENTS_MODEL", "gpt-4o-mini"),
    api_key=_settings.OPENAI_API_KEY,
    base_url=getattr(_settings, "OPENAI_BASE_URL", None),
    enable_tracing=getattr(_settings, "AGENT_TRACING_ENABLED", True),
    skills_dir=_settings.SKILLS_DIR,
    sandbox_dir=_settings.SANDBOX_DIR,
)

_runtime = AgentRuntime(
    adapter=_adapter,
    repo=_repo,
    session_db_path=getattr(_settings, "AGENT_SESSION_DB", "runtime/agent/sessions.db"),
    enable_tracing=getattr(_settings, "AGENT_TRACING_ENABLED", True),
)


def get_agent_task_service() -> AgentTaskService:
    return AgentTaskService(_repo, _runtime)


@router.post("")
@router.post("/agents/{agent_id}/run")
@router.post("/run")
async def copilotkit_agent_run(
    request: Request,
    agent_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_agent_task_service),
):
    """
    CopilotKit AG-UI 兼容端点。

    接受 @ag-ui/client HttpAgent 的标准 POST 请求，
    返回 AG-UI 标准 SSE 事件流。

    请求体：
    {
      "threadId": "...",
      "runId": "...",
      "messages": [...],
      "state": {...},
      "tools": [...],
      "context": [...],
      "forwardedProps": {...}
    }
    """
    # 解析请求体
    body = await request.json()
    agui_req = AgUiRequest.from_dict(body)
    thread_id = agui_req.thread_id or f"thread_{uuid.uuid4().hex[:12]}"
    run_id = agui_req.run_id

    # 提取用户最后一条消息
    user_input = ""
    for msg in reversed(agui_req.messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                user_input = content
                break
            elif isinstance(content, list):
                # HuggingFace 格式：content = [{ type: "text", text: "..." }]
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        user_input = part.get("text", "")
                        break
                if user_input:
                    break

    if not user_input:
        logger.warning("AG-UI request: no user message found in messages")
        user_input = "Hello"

    # 从 forwardedProps 获取额外上下文
    forwarded = agui_req.forwarded_props or {}
    auth_token = forwarded.get("auth_token", "")
    auth_header = request.headers.get("authorization", "")
    if not auth_token and auth_header.startswith("Bearer "):
        auth_token = auth_header.replace("Bearer ", "")

    # 确保 task 存在 — 用 thread_id 作为 task_id
    task_id = thread_id
    try:
        await service.get_task(user["id"], task_id)
    except Exception:
        # AG-UI 用 thread_id 作为 task_id，直接通过 service 的 repo 创建
        from ...agent_platform.models import AgentTask, AgentTaskStatus
        task = AgentTask(
            task_id=task_id,
            user_id=user["id"],
            task_type="conversation",
            title=f"AG-UI {thread_id[:12]}",
            status=AgentTaskStatus.PENDING,
        )
        await service._repo.create(task)

    logger.bind(thread_id=thread_id, run_id=run_id).info(
        f"AG-UI run started: {user_input[:100]}"
    )

    async def event_generator():
        """SSE 事件生成器 - 输出 AG-UI 标准格式"""
        try:
            # 提取初始 state（如果存在）
            existing_state = agui_req.state or {}
            if existing_state:
                # 如果前端带了 state，先回传一次 StateSnapshot
                from ...agent_platform.adapters.agui_events import StateSnapshotEvent
                yield StateSnapshotEvent(snapshot=existing_state).to_sse() + "\n"

            # 运行 ANIFORCE AgentRuntime
            aniforce_events = service.run_task(
                user_id=user["id"],
                task_id=task_id,
                user_input=user_input,
                context={"auth_token": auth_token},
            )

            # 适配为 AG-UI SSE
            async for sse_chunk in agui_sse_generator(
                aniforce_events,
                thread_id=thread_id,
                run_id=run_id,
                tool_registry=_global_tool_registry,
            ):
                yield sse_chunk

        except Exception as e:
            logger.exception(f"AG-UI stream error: {e}")
            from ...agent_platform.adapters.agui_events import RunErrorEvent
            yield RunErrorEvent(message=str(e)).to_sse() + "\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
        },
    )


@router.get("/health")
async def copilotkit_health(
    user: dict = Depends(get_current_user),
):
    """CopilotKit runtime 健康检查"""
    return {
        "status": "ok",
        "protocol": "ag-ui",
        "version": "0.1.0",
        "capabilities": {
            "streaming": True,
            "state_management": True,
            "activity_messages": True,
        },
    }
