"""广告投放 Schema"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CampaignBase(BaseModel):
    """广告投放基础 Schema"""
    name: str = Field(..., min_length=1, max_length=255, description="广告计划名称")
    description: Optional[str] = Field(None, description="描述")
    platform: str = Field(..., description="投放平台 (TikTok/Google/Meta)")
    budget: float = Field(..., ge=0, description="预算")
    target_cpa: Optional[float] = Field(None, ge=0, description="目标 CPA")
    pipeline_step: Optional[str] = Field(None, max_length=50, description="Pipeline 阶段")
    learning_phase: Optional[str] = Field(None, max_length=50, description="学习阶段")
    auto_optimize_enabled: bool = Field(default=False, description="自动优化开关")
    optimization_rules: Optional[list[str]] = Field(default_factory=list, description="优化规则列表")
    material_ids: Optional[list[str]] = Field(default_factory=list, description="素材 ID 列表")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    config: Optional[dict] = Field(None, description="配置信息")


class CampaignCreate(CampaignBase):
    """创建广告投放 Schema"""
    project_id: str = Field(..., description="项目 ID")


class CampaignUpdate(BaseModel):
    """更新广告投放 Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="广告计划名称")
    description: Optional[str] = Field(None, description="描述")
    platform: Optional[str] = Field(None, description="投放平台")
    budget: Optional[float] = Field(None, ge=0, description="预算")
    target_cpa: Optional[float] = Field(None, ge=0, description="目标 CPA")
    status: Optional[str] = Field(None, description="状态")
    pipeline_step: Optional[str] = Field(None, max_length=50, description="Pipeline 阶段")
    learning_phase: Optional[str] = Field(None, max_length=50, description="学习阶段")
    auto_optimize_enabled: Optional[bool] = Field(None, description="自动优化开关")
    optimization_rules: Optional[list[str]] = Field(None, description="优化规则列表")
    material_ids: Optional[list[str]] = Field(None, description="素材 ID 列表")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    config: Optional[dict] = Field(None, description="配置信息")


class CampaignResponse(CampaignBase):
    """广告投放响应 Schema"""
    id: str = Field(..., description="广告计划 ID")
    project_id: str = Field(..., description="项目 ID")
    spent: float = Field(default=0.0, description="已消耗")
    status: str = Field(..., description="状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    # 计算字段（可选，由 Service 层从 Metrics 聚合）
    installs: Optional[int] = Field(None, description="总安装数")
    roi: Optional[float] = Field(None, description="ROI")
    cpi: Optional[float] = Field(None, description="实际 CPI")
    ctr: Optional[float] = Field(None, description="CTR")
    cvr: Optional[float] = Field(None, description="CVR")

    class Config:
        from_attributes = True


class CampaignListResponse(BaseModel):
    """广告投放列表响应 Schema"""
    items: list[CampaignResponse]
    total: int
    page: int
    page_size: int
