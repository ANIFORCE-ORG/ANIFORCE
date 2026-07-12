"""Agent Run HTTP transport routes."""

from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.api.common import authorization, error_payload
from app.agent.runs.commands import AgentRunCommands, CreateRunCommand
from app.api.deps import get_current_user
from app.config.database import get_db, get_session_maker
from app.repositories.impl.sqlite_agent_run_repo import SqliteAgentRunRepository
from app.agent.gateway import AgentGatewayError, AgentGatewayService
from app.agent.runs.service import AgentRunError, AgentRunService
from app.agent.sessions.service import AgentSessionError

router = APIRouter()


def get_agent_gateway() -> AgentGatewayService:
    return AgentGatewayService()


@router.post("/tasks/{task_id}/cancel")
async def cancel_agent_task(task_id: str, current_user: dict = Depends(get_current_user)):
    raise HTTPException(
        status_code=410,
        detail=error_payload(
            "TASK_CANCEL_REMOVED",
            "Task cancellation has moved to /api/v1/agent/runs/{run_id}/cancel",
            False,
            {"task_id": task_id, "user_id": current_user["id"]},
        ),
    )


@router.get("/runs/{run_id}")
async def get_agent_run(
    run_id: str,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    try:
        return await AgentRunService(SqliteAgentRunRepository(session)).get(run_id, current_user["id"])
    except AgentRunError as exc:
        raise HTTPException(status_code=exc.status_code, detail=error_payload(exc.code, exc.message, exc.retryable)) from exc


@router.post("/runs/{run_id}/cancel")
async def cancel_agent_run(
    run_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    gateway: AgentGatewayService = Depends(get_agent_gateway),
):
    service = AgentRunService(SqliteAgentRunRepository(session))
    try:
        run = await service.get(run_id, current_user["id"])
        updated = await service.request_cancel(run_id, current_user["id"])
        await session.commit()
    except AgentRunError as exc:
        raise HTTPException(status_code=exc.status_code, detail=error_payload(exc.code, exc.message, exc.retryable)) from exc
    try:
        await gateway.cancel_run(authorization(request), run_id)
    except AgentGatewayError:
        pass
    return {"run_id": run_id, "session_id": run["session_id"], "status": updated["status"]}


@router.post("/runs")
async def run_agent(request: Request, current_user: dict = Depends(get_current_user)):
    started = perf_counter()
    body = await request.json()
    prompt = body.get("prompt", "")
    try:
        result = await AgentRunCommands(get_session_maker()).create(
            CreateRunCommand(
                user_id=current_user["id"],
                prompt=prompt,
                requested_session_id=body.get("session_id"),
                task_type=body.get("task_type", "conversation"),
                context_snapshot=body.get("context_snapshot"),
                idempotency_key=body.get("idempotency_key") or request.headers.get("Idempotency-Key"),
            )
        )
    except (AgentRunError, AgentSessionError) as exc:
        details = {"run": exc.run} if isinstance(exc, AgentRunError) else None
        raise HTTPException(status_code=exc.status_code, detail=error_payload(exc.code, exc.message, exc.retryable, details)) from exc
    run = result.run
    if result.reused:
        return {"run_id": run["run_id"], "session_id": result.session_id, "status": run["status"], "reused": True}
    logger.bind(run_id=run["run_id"], session_id=result.session_id, user_id=current_user["id"]).info(
        "[PERF][agent_first_token] backend.run_start total_ms={} prompt_chars={} context_chars={}",
        int((perf_counter() - started) * 1000),
        len(prompt),
        len(result.business_context_summary or ""),
    )
    return {"run_id": run["run_id"], "session_id": result.session_id, "status": "queued"}
