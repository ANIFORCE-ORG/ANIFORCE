"""AI Gateway request and response schemas."""
from typing import Any, Literal

from pydantic import BaseModel, Field


AIScenario = Literal[
    "project_draft",
    "plan_extract",
    "material_recommend",
    "material_copy",
    "plan_review",
    "campaign_diagnosis",
    "report_summary",
    "chat_general",
]


class AIMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(..., max_length=8000)


class AIRunRequest(BaseModel):
    scenario: AIScenario
    project_id: str | None = None
    campaign_id: str | None = None
    material_id: str | None = None
    messages: list[AIMessage] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    response_schema: dict[str, Any] | None = None


class AIUsagePayload(BaseModel):
    usage_log_id: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    daily_limit_remaining: int | None = None


class AIRunResponse(BaseModel):
    scenario: AIScenario
    status: Literal["draft", "suggested", "blocked", "failed"]
    output: dict[str, Any]
    usage: AIUsagePayload
    requires_human_confirm: bool = True


class AIUsageSummary(BaseModel):
    total_tokens: int
    estimated_cost_usd: float
    by_scenario: dict[str, Any]


class AIBudgetRequest(BaseModel):
    scope_type: Literal["user", "project"] = "user"
    scope_id: str | None = None
    daily_token_limit: int | None = Field(None, gt=0)
    monthly_token_limit: int | None = Field(None, gt=0)
    daily_cost_limit_usd: float | None = Field(None, ge=0)
    monthly_cost_limit_usd: float | None = Field(None, ge=0)
    enabled: bool = True

