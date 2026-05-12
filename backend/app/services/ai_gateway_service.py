"""Controlled AI Gateway service."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.models.ai_usage import AIBudget, AIOutput, AIUsageLog
from app.schemas.ai import AIRunRequest
from app.services.ai_scenarios import get_scenario_config, mock_output_for_scenario


class AIGatewayService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()

    def _estimate_tokens(self, request: AIRunRequest) -> int:
        payload = request.model_dump_json()
        return max(len(payload) // 4, 1)

    def _resolve_model(self, model_tier: str) -> str:
        if model_tier == "large":
            return self.settings.AI_LARGE_MODEL or self.settings.AI_DEFAULT_MODEL
        if model_tier == "medium":
            return self.settings.AI_MEDIUM_MODEL or self.settings.AI_DEFAULT_MODEL
        return self.settings.AI_SMALL_MODEL or self.settings.AI_DEFAULT_MODEL

    async def _daily_usage(self, user_id: str) -> int:
        today = datetime.utcnow().date()
        result = await self.session.execute(
            select(func.coalesce(func.sum(AIUsageLog.total_tokens), 0)).where(
                AIUsageLog.user_id == user_id,
                func.date(AIUsageLog.created_at) == today.isoformat(),
            )
        )
        return int(result.scalar_one() or 0)

    async def _resolve_budget(self, user_id: str) -> int:
        result = await self.session.execute(
            select(AIBudget).where(
                AIBudget.scope_type == "user",
                AIBudget.scope_id == user_id,
                AIBudget.enabled == True,  # noqa: E712
            )
        )
        budget = result.scalar_one_or_none()
        return int(
            (budget.daily_token_limit if budget and budget.daily_token_limit else None)
            or self.settings.AI_DAILY_TOKEN_LIMIT
        )

    async def run(self, user_id: str, request: AIRunRequest) -> dict[str, Any]:
        scenario_config = get_scenario_config(request.scenario)
        input_tokens = self._estimate_tokens(request)
        if input_tokens > scenario_config.input_token_limit:
            raise ValueError(f"Input token estimate exceeds scenario limit: {scenario_config.input_token_limit}")

        daily_limit = await self._resolve_budget(user_id)
        daily_used = await self._daily_usage(user_id)
        planned_total = input_tokens + scenario_config.output_token_limit
        if daily_used + planned_total > daily_limit:
            raise ValueError("AI daily token budget exceeded")

        provider = self.settings.AI_PROVIDER or "mock"
        model = self._resolve_model(scenario_config.default_model_tier)
        request_hash = hashlib.sha256(request.model_dump_json().encode("utf-8")).hexdigest()

        output = mock_output_for_scenario(
            request.scenario,
            {
                **request.context,
                "project_id": request.project_id,
                "campaign_id": request.campaign_id,
                "material_id": request.material_id,
            },
        )
        output_tokens = max(len(json.dumps(output, ensure_ascii=False)) // 4, 1)
        usage_log = AIUsageLog(
            user_id=user_id,
            project_id=request.project_id,
            campaign_id=request.campaign_id,
            scenario=request.scenario,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            estimated_cost_usd=0.0,
            request_hash=request_hash,
            prompt_version="v0.2-day1",
            status="success",
        )
        self.session.add(usage_log)
        await self.session.flush()

        ai_output = AIOutput(
            usage_log_id=usage_log.id,
            scenario=request.scenario,
            project_id=request.project_id,
            campaign_id=request.campaign_id,
            material_id=request.material_id,
            output_json=json.dumps(output, ensure_ascii=False),
            status=scenario_config.output_status,
        )
        self.session.add(ai_output)
        await self.session.commit()

        return {
            "scenario": request.scenario,
            "status": scenario_config.output_status,
            "output": output,
            "usage": {
                "usage_log_id": usage_log.id,
                "provider": provider,
                "model": model,
                "input_tokens": usage_log.input_tokens,
                "output_tokens": usage_log.output_tokens,
                "total_tokens": usage_log.total_tokens,
                "estimated_cost_usd": usage_log.estimated_cost_usd,
                "daily_limit_remaining": max(daily_limit - daily_used - usage_log.total_tokens, 0),
            },
            "requires_human_confirm": scenario_config.requires_human_confirm,
        }

