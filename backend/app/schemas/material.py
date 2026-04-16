"""素材 Schema"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class MaterialBase(BaseModel):
    """素材基础 Schema"""
    name: Optional[str] = Field(None, max_length=255, description="素材名称")
    type: str = Field(..., description="素材类型 (a_segment/b_segment/c_segment/full_video)")
    media_type: Optional[str] = Field(None, max_length=20, description="媒体类型 (video/image)")
    url: str = Field(..., description="素材 URL")
    thumbnail_url: Optional[str] = Field(None, description="缩略图 URL")
    ctr_estimate: Optional[float] = Field(None, ge=0, le=1, description="CTR 预估")
    fatigue: float = Field(default=0.0, ge=0, description="疲劳度")
    is_hero: bool = Field(default=False, description="是否英雄素材")
    tags: Optional[list[str]] = Field(default_factory=list, description="标签列表")
    duration: Optional[int] = Field(None, ge=0, description="时长（秒）")
    file_size: Optional[int] = Field(None, ge=0, description="文件大小（字节）")
    project_ids: Optional[list[str]] = Field(default_factory=list, description="关联项目 ID 列表")
    campaign_ids: Optional[list[str]] = Field(default_factory=list, description="关联广告计划 ID 列表")


class MaterialCreate(MaterialBase):
    """创建素材 Schema"""
    pass


class MaterialUpdate(BaseModel):
    """更新素材 Schema"""
    name: Optional[str] = Field(None, max_length=255, description="素材名称")
    type: Optional[str] = Field(None, description="素材类型")
    media_type: Optional[str] = Field(None, max_length=20, description="媒体类型")
    status: Optional[str] = Field(None, description="状态")
    url: Optional[str] = Field(None, description="素材 URL")
    thumbnail_url: Optional[str] = Field(None, description="缩略图 URL")
    ctr_estimate: Optional[float] = Field(None, ge=0, le=1, description="CTR 预估")
    fatigue: Optional[float] = Field(None, ge=0, description="疲劳度")
    is_hero: Optional[bool] = Field(None, description="是否英雄素材")
    tags: Optional[list[str]] = Field(None, description="标签列表")
    duration: Optional[int] = Field(None, ge=0, description="时长（秒）")
    file_size: Optional[int] = Field(None, ge=0, description="文件大小（字节）")
    project_ids: Optional[list[str]] = Field(None, description="关联项目 ID 列表")
    campaign_ids: Optional[list[str]] = Field(None, description="关联广告计划 ID 列表")


class MaterialResponse(MaterialBase):
    """素材响应 Schema"""
    id: str = Field(..., description="素材 ID")
    user_id: str = Field(..., description="用户 ID")
    status: str = Field(..., description="状态")
    created_at: datetime = Field(..., description="创建时间")

    # 计算字段（可选，由 Service 层从关联的 Campaign Metrics 聚合）
    ctr: Optional[float] = Field(None, description="实际 CTR")
    cvr: Optional[float] = Field(None, description="CVR")
    roi: Optional[float] = Field(None, description="ROI")
    spend: Optional[float] = Field(None, description="消耗")

    class Config:
        from_attributes = True


class MaterialListResponse(BaseModel):
    """素材列表响应 Schema"""
    items: list[MaterialResponse]
    total: int
    page: int
    page_size: int


class MaterialUploadRequest(BaseModel):
    """素材上传请求 Schema"""
    name: Optional[str] = Field(None, description="素材名称")
    type: str = Field(..., description="素材类型")
    media_type: str = Field(..., description="媒体类型 (video/image)")
    tags: Optional[list[str]] = Field(default_factory=list, description="标签列表")
    project_ids: Optional[list[str]] = Field(default_factory=list, description="关联项目 ID")


class MaterialLinkCampaignRequest(BaseModel):
    """素材关联广告计划请求 Schema"""
    material_ids: list[str] = Field(..., min_length=1, description="素材 ID 列表")
    campaign_id: str = Field(..., description="广告计划 ID")
    action: str = Field(..., description="操作类型 (link/unlink)")
