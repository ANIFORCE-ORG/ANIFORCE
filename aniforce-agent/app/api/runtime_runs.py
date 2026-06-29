"""Runtime-only Agent Run API.

This API is called by backend after product session/run validation. It reuses
the local Task runtime as an implementation detail, but does not expose product
task lifecycle semantics to callers.
"""

import asyncio
import json
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger

from app.auth import get_current_user
from app.services.agent_task_service import AgentTaskService

router = APIRouter(prefix="/runtime/runs", tags=["runtime-runs"])

_ACTIVE_RUNTIME_RUNS: dict[str, dict] = {}


def _elapsed_ms(start: float) -> int:
    return int((perf_counter() - start) * 1000)


def get_service() -> AgentTaskService:
    from app.main import _service
    return _service


@router.post("")
async def run_runtime(
    request: Request,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_service),
):
    request_start = perf_counter()
    body = await request.json()
    prompt = body.get("prompt", "")
    session_id = body.get("session_id")
    run_id = body.get("run_id")
    user_id = body.get("user_id") or user["id"]
    auth_token = body.get("auth_token") or ""
    business_context_summary = body.get("business_context_summary", "")
    task_type = body.get("task_type", "conversation")

    if not run_id:
        raise HTTPException(status_code=422, detail={"code": "RUN_ID_REQUIRED", "message": "run_id is required"})
    if not session_id:
        raise HTTPException(status_code=422, detail={"code": "SESSION_ID_REQUIRED", "message": "session_id is required"})

    context = {
        "auth_token": str(auth_token).removeprefix("Bearer "),
        "business_context_summary": business_context_summary,
        "run_meta": {"run_id": run_id, "user_id": user_id},
    }

    task = await service.create_task(
        user_id=user_id,
        task_type=task_type,
        title=prompt[:50] if prompt else "Agent Runtime Run",
        session_id=session_id,
    )
    _ACTIVE_RUNTIME_RUNS[run_id] = {"task_id": task.task_id, "user_id": user_id}
    perf_log = logger.bind(run_id=run_id, task_id=task.task_id, session_id=session_id, user_id=user_id)
    perf_log.debug(
        "[PERF][agent_first_token] runtime_api.pre_stream total_ms={} prompt_chars={} context_chars={}",
        _elapsed_ms(request_start),
        len(prompt),
        len(business_context_summary or ""),
    )

    async def event_generator():
        active = _ACTIVE_RUNTIME_RUNS.get(run_id)
        if active and active.get("task_id") == task.task_id:
            active["stream_task"] = asyncio.current_task()
            if active.get("cancel_requested"):
                perf_log.debug("runtime run stream cancelled before start")
                return
        try:
            async for event in service.run_task(
                user_id=user_id,
                task_id=task.task_id,
                user_input=prompt,
                context=context,
            ):
                payload = dict(event.payload or {})
                payload.setdefault("run_id", run_id)
                payload.setdefault("task_id", task.task_id)
                yield f"id: {event.sequence}\n"
                yield f"event: {event.event_type}\n"
                yield f"data: {json.dumps(payload, default=str, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            perf_log.debug("runtime run stream cancelled")
            raise
        except Exception as exc:
            perf_log.exception("runtime run failed")
            yield "event: runtime.error\n"
            yield f"data: {json.dumps({'run_id': run_id, 'message': str(exc)}, ensure_ascii=False)}\n\n"
        finally:
            active = _ACTIVE_RUNTIME_RUNS.get(run_id)
            if active and active.get("task_id") == task.task_id:
                _ACTIVE_RUNTIME_RUNS.pop(run_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{run_id}/cancel")
async def cancel_runtime_run(
    run_id: str,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_service),
):
    active = _ACTIVE_RUNTIME_RUNS.get(run_id)
    if not active:
        return {"run_id": run_id, "status": "not_running"}
    if active.get("user_id") != user["id"]:
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": "Run not found"})

    try:
        await service.cancel_task(user["id"], active["task_id"])
    except Exception as exc:
        logger.bind(run_id=run_id, task_id=active["task_id"], user_id=user["id"]).warning(
            "runtime run cancel failed: {}", exc
        )
        return {"run_id": run_id, "task_id": active["task_id"], "status": "cancel_unavailable"}

    active["cancel_requested"] = True
    stream_task = active.get("stream_task")
    if stream_task and not stream_task.done():
        stream_task.cancel()

    return {"run_id": run_id, "task_id": active["task_id"], "status": "cancel_requested"}
