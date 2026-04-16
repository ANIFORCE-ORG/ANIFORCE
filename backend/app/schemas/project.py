"""项目 Schema"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProjectBase(BaseModel):
    """项目基础 Schema"""
    name: str = Field(..., min_length=1, max_length=255, description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    game_type: Optional[str] = Field(None, max_length=50, description="游戏类型")
    product_type: Optional[str] = Field(None, max_length=50, description="产品类型")
    target_market: Optional[str] = Field(None, max_length=100, description="目标市场")
    region: Optional[list[str]] = Field(default_factory=list, description="目标地区列表")
    tags: Optional[list[str]] = Field(default_factory=list, description="标签列表")
    total_budget: float = Field(..., ge=0, description="总预算")
    target_roi: Optional[float] = Field(None, ge=0, description="目标 ROI")
    manager: Optional[str] = Field(None, max_length=100, description="负责人")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")


class ProjectCreate(ProjectBase):
    """创建项目 Schema"""
    pass


class ProjectUpdate(BaseModel):
    """更新项目 Schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    game_type: Optional[str] = Field(None, max_length=50, description="游戏类型")
    product_type: Optional[str] = Field(None, max_length=50, description="产品类型")
    target_market: Optional[str] = Field(None, max_length=100, description="目标市场")
    region: Optional[list[str]] = Field(None, description="目标地区列表")
    tags: Optional[list[str]] = Field(None, description="标签列表")
    total_budget: Optional[float] = Field(None, ge=0, description="总预算")
    target_roi: Optional[float] = Field(None, ge=0, description="目标 ROI")
    status: Optional[str] = Field(None, description="项目状态")
    manager: Optional[str] = Field(None, max_length=100, description="负责人")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")


class ProjectResponse(ProjectBase):
    """项目响应 Schema"""
    id: str = Field(..., description="项目 ID")
    user_id: str = Field(..., description="用户 ID")
    spent: float = Field(default=0.0, description="已消耗预算")
    status: str = Field(..., description="项目状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    # 计算字段（可选，由 Service 层计算）
    current_roi: Optional[float] = Field(None, description="当前 ROI")
    installs: Optional[int] = Field(None, description="总安装数")
    campaign_count: Optional[int] = Field(None, description="关联计划数")

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """项目列表响应 Schema"""
    items: list[ProjectResponse]
    total: int
    page: int
    page_size: int
