"""Agent Run API（流式执行）"""

import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.auth import get_current_user
from app.services.agent_task_service import AgentTaskService
from app.models.agent_platform_models import AgentTaskStatus

router = APIRouter(prefix="/runs", tags=["runs"])


def get_service() -> AgentTaskService:
    from app.main import _service
    return _service


@router.post("")
async def run_agent(
    request: Request,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_service),
):
    """
    流式执行 Agent（SSE）

    请求体：
    {
        "prompt": "用户输入",
        "session_id": "可选，续接对话",
        "task_type": "conversation",
        "context": {"auth_token": "..."}  # 可选，用于 MCP
    }
    """
    body = await request.json()
    prompt = body.get("prompt", "")
    session_id = body.get("session_id")
    task_type = body.get("task_type", "conversation")
    context = body.get("context", {})
    business_context_summary = body.get("business_context_summary", "")
    run_meta = body.get("run_meta", {})
    if business_context_summary:
        context["business_context_summary"] = business_context_summary
    if run_meta:
        context["run_meta"] = run_meta

    # 传递 JWT token 给 MCP
    if "token" in user and "auth_token" not in context:
        context["auth_token"] = user["token"]

    # 创建或校验 session：生产环境不允许跨用户 resume 任意 session_id
    if session_id:
        await service.get_active_session(user["id"], session_id)
    else:
        session = await service.create_session(
            user_id=user["id"],
            title=prompt[:50] if prompt else "新对话",
        )
        session_id = session.session_id

    # 创建 task（一次 run/turn 对应一个 task）
    task = await service.create_task(
        user_id=user["id"],
        task_type=task_type,
        title=prompt[:50] if prompt else "Agent Task",
        session_id=session_id,
    )

    async def event_generator():
        try:
            async for event in service.run_task(
                user_id=user["id"],
                task_id=task.task_id,
                user_input=prompt,
                context=context,
            ):
                yield f"id: {event.sequence}\n"
                yield f"event: {event.event_type}\n"
                yield f"data: {json.dumps(event.payload, default=str, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"event: error\n"
            yield f"data: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
