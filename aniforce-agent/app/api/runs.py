"""Agent Run API（流式执行）"""

import json
from time import perf_counter

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from loguru import logger

from app.auth import get_current_user
from app.services.agent_task_service import AgentTaskService

router = APIRouter(prefix="/runs", tags=["runs"])


def _elapsed_ms(start: float) -> int:
    return int((perf_counter() - start) * 1000)


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
    request_start = perf_counter()
    body = await request.json()
    body_parse_ms = _elapsed_ms(request_start)
    prompt = body.get("prompt", "")
    session_id = body.get("session_id")
    task_type = body.get("task_type", "conversation")
    context = body.get("context", {})
    business_context_summary = body.get("business_context_summary", "")
    run_meta = body.get("run_meta", {})
    run_id = str(run_meta.get("run_id") or "")
    perf_log = logger.bind(run_id=run_id, session_id=session_id, user_id=user["id"])
    if business_context_summary:
        context["business_context_summary"] = business_context_summary
    if run_meta:
        context["run_meta"] = run_meta

    # 传递 JWT token 给 MCP
    if "token" in user and "auth_token" not in context:
        context["auth_token"] = user["token"]

    # 创建或校验 session：生产环境不允许跨用户 resume 任意 session_id
    session_start = perf_counter()
    if session_id:
        await service.get_active_session(user["id"], session_id)
    else:
        session = await service.create_session(
            user_id=user["id"],
            title=prompt[:50] if prompt else "新对话",
        )
        session_id = session.session_id
    session_ms = _elapsed_ms(session_start)

    # 创建 task（一次 run/turn 对应一个 task）
    task_start = perf_counter()
    task = await service.create_task(
        user_id=user["id"],
        task_type=task_type,
        title=prompt[:50] if prompt else "Agent Task",
        session_id=session_id,
    )
    task_ms = _elapsed_ms(task_start)
    perf_log = perf_log.bind(task_id=task.task_id, session_id=session_id)
    perf_log.info(
        "[PERF][agent_first_token] agent_api.pre_stream total_ms={} body_parse_ms={} session_ms={} task_create_ms={} prompt_chars={} context_chars={}",
        _elapsed_ms(request_start),
        body_parse_ms,
        session_ms,
        task_ms,
        len(prompt),
        len(business_context_summary or ""),
    )

    async def event_generator():
        stream_start = perf_counter()
        first_event_logged = False
        first_delta_logged = False
        try:
            async for event in service.run_task(
                user_id=user["id"],
                task_id=task.task_id,
                user_input=prompt,
                context=context,
            ):
                if not first_event_logged:
                    first_event_logged = True
                    perf_log.info(
                        "[PERF][agent_first_token] agent_api.first_event total_ms={} stream_wait_ms={} event_type={}",
                        _elapsed_ms(request_start),
                        _elapsed_ms(stream_start),
                        event.event_type,
                    )
                if not first_delta_logged and event.event_type == "message.updated":
                    first_delta_logged = True
                    perf_log.info(
                        "[PERF][agent_first_token] agent_api.first_message_delta total_ms={} stream_wait_ms={} sequence={}",
                        _elapsed_ms(request_start),
                        _elapsed_ms(stream_start),
                        event.sequence,
                    )
                if event.event_type == "thinking.updated":
                    perf_log.info(
                        "[PERF][agent_first_token] agent_api.thinking_delta seq={} delta_chars={}",
                        event.sequence,
                        len(str(event.payload.get("delta", ""))),
                    )
                yield f"id: {event.sequence}\n"
                yield f"event: {event.event_type}\n"
                yield f"data: {json.dumps(event.payload, default=str, ensure_ascii=False)}\n\n"
        except Exception as e:
            perf_log.exception("[PERF][agent_first_token] agent_api.stream_error total_ms={}", _elapsed_ms(request_start))
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
