"""Controlled AI Gateway API."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config.database import get_db
from app.models.ai_usage import AIBudget, AIUsageLog
from app.schemas.ai import AIBudgetRequest, AIRunRequest, AIRunResponse
from app.services.ai_gateway_service import AIGatewayService

router = APIRouter(prefix="/ai", tags=["AI Gateway"])


@router.post("/run", response_model=AIRunResponse)
async def run_ai(
    request: AIRunRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    try:
        return await AIGatewayService(session).run(current_user["id"], request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/usage/summary")
async def get_ai_usage_summary(
    project_id: str | None = None,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    filters = [AIUsageLog.user_id == current_user["id"]]
    if project_id:
        filters.append(AIUsageLog.project_id == project_id)

    result = await session.execute(
        select(
            AIUsageLog.scenario,
            func.coalesce(func.sum(AIUsageLog.total_tokens), 0),
            func.coalesce(func.sum(AIUsageLog.estimated_cost_usd), 0),
        )
        .where(*filters)
        .group_by(AIUsageLog.scenario)
    )
    by_scenario = {
        scenario: {
            "total_tokens": int(total_tokens or 0),
            "estimated_cost_usd": float(cost or 0),
        }
        for scenario, total_tokens, cost in result.all()
    }
    return {
        "total_tokens": sum(item["total_tokens"] for item in by_scenario.values()),
        "estimated_cost_usd": sum(item["estimated_cost_usd"] for item in by_scenario.values()),
        "by_scenario": by_scenario,
    }


@router.get("/usage/logs")
async def get_ai_usage_logs(
    project_id: str | None = None,
    scenario: str | None = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    filters = [AIUsageLog.user_id == current_user["id"]]
    if project_id:
        filters.append(AIUsageLog.project_id == project_id)
    if scenario:
        filters.append(AIUsageLog.scenario == scenario)
    result = await session.execute(
        select(AIUsageLog)
        .where(*filters)
        .order_by(AIUsageLog.created_at.desc())
        .limit(limit)
    )
    return [
        {
            "id": log.id,
            "project_id": log.project_id,
            "campaign_id": log.campaign_id,
            "scenario": log.scenario,
            "provider": log.provider,
            "model": log.model,
            "input_tokens": log.input_tokens,
            "output_tokens": log.output_tokens,
            "total_tokens": log.total_tokens,
            "estimated_cost_usd": log.estimated_cost_usd,
            "status": log.status,
            "error_message": log.error_message,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in result.scalars().all()
    ]


@router.post("/usage/budget")
async def set_ai_usage_budget(
    request: AIBudgetRequest,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    scope_id = request.scope_id or current_user["id"]
    if request.scope_type == "user" and scope_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Cannot set another user's AI budget")

    result = await session.execute(
        select(AIBudget).where(
            AIBudget.scope_type == request.scope_type,
            AIBudget.scope_id == scope_id,
        )
    )
    budget = result.scalar_one_or_none()
    if not budget:
        budget = AIBudget(scope_type=request.scope_type, scope_id=scope_id)
        session.add(budget)

    for key, value in request.model_dump(exclude_unset=True).items():
        if key != "scope_id" and hasattr(budget, key):
            setattr(budget, key, value)
    budget.scope_id = scope_id
    await session.commit()
    return {
        "id": budget.id,
        "scope_type": budget.scope_type,
        "scope_id": budget.scope_id,
        "daily_token_limit": budget.daily_token_limit,
        "monthly_token_limit": budget.monthly_token_limit,
        "daily_cost_limit_usd": budget.daily_cost_limit_usd,
        "monthly_cost_limit_usd": budget.monthly_cost_limit_usd,
        "enabled": budget.enabled,
    }
