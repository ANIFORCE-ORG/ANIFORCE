"""Schemas for campaign material bindings and batch plan creation."""
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CampaignMaterialCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    material_id: str = Field(..., description="素材 ID")
    title: str | None = Field(None, max_length=120, description="该计划下的素材标题")
    description: str | None = Field(None, max_length=500, description="该计划下的素材描述")
    ad_copy: str | None = Field(None, alias="copy", max_length=1000, description="投放文案")
    source: Literal["manual", "upload", "ai", "copied"] = "manual"
    sort_order: int = Field(0, ge=0)
    status: Literal["draft", "ready", "disabled"] = "draft"


class CampaignMaterialUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str | None = Field(None, max_length=120)
    description: str | None = Field(None, max_length=500)
    ad_copy: str | None = Field(None, alias="copy", max_length=1000)
    source: Literal["manual", "upload", "ai", "copied"] | None = None
    sort_order: int | None = Field(None, ge=0)
    status: Literal["draft", "ready", "disabled"] | None = None


class CampaignMaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    campaign_id: str
    material_id: str
    title: str | None = None
    description: str | None = None
    ad_copy: str | None = Field(None, alias="copy")
    source: str | None = None
    sort_order: int = 0
    status: str
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime
    material: dict[str, Any] | None = None

class TargetingPayload(BaseModel):
    regions: list[str] = Field(default_factory=list)
    age_range: dict[str, Any] = Field(default_factory=dict)
    gender: str = "all"
    interests: list[str] = Field(default_factory=list)


class BatchCampaignCreateRequest(BaseModel):
    plan_count: int = Field(..., ge=0, le=99)
    name_template: str = Field(..., min_length=1, max_length=180)
    platform: str = Field(..., description="Meta/TikTok/Google")
    platform_account_id: str | None = None
    objective: str | None = None
    budget_type: Literal["daily", "total", "lifetime"] = "total"
    budget: float = Field(..., gt=0)
    target_cpa: float | None = Field(None, ge=0)
    bidding_strategy: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    targeting: TargetingPayload = Field(default_factory=TargetingPayload)
    materials: list[CampaignMaterialCreate] = Field(default_factory=list)
    status: str = "draft"
    auto_optimize_enabled: bool = True

    @model_validator(mode="after")
    def validate_dates(self) -> "BatchCampaignCreateRequest":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return self


class BatchCampaignCreateResponse(BaseModel):
    campaigns: list[dict[str, Any]]
    material_bindings: list[CampaignMaterialResponse]
    plan_count: int
    skipped: bool = False
    message: str | None = None
