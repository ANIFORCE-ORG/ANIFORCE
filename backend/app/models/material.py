"""素材模型"""
import uuid
import enum
import json
from datetime import datetime
from sqlalchemy import String, Float, DateTime, Enum, Text, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base


class MaterialType(str, enum.Enum):
    """素材类型"""
    A_SEGMENT = "a_segment"
    B_SEGMENT = "b_segment"
    C_SEGMENT = "c_segment"
    FULL_VIDEO = "full_video"


class MaterialStatus(str, enum.Enum):
    """素材状态"""
    RUNNING = "running"      # 投放中
    READY = "ready"          # 待投放
    FATIGUE = "fatigue"      # 已疲劳


class Material(Base):
    __tablename__ = "materials"
    __table_args__ = (
        Index("ix_materials_user_checksum", "user_id", "checksum_sha256"),
        Index("ix_materials_user_lifecycle", "user_id", "lifecycle_status"),
        Index("ix_materials_user_processing", "user_id", "processing_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 关联关系（多对多）
    project_ids: Mapped[str | None] = mapped_column(Text, nullable=True)   # JSON 数组
    campaign_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组
    
    # 素材信息
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type: Mapped[MaterialType] = mapped_column(Enum(MaterialType), nullable=False, index=True)
    status: Mapped[MaterialStatus] = mapped_column(Enum(MaterialStatus), nullable=False, default=MaterialStatus.READY, index=True)
    lifecycle_status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    processing_status: Mapped[str] = mapped_column(String(20), nullable=False, default="ready", index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    storage_object_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # 预估数据
    ctr_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组
    
    # 元数据
    media_kind: Mapped[str | None] = mapped_column(String(20), nullable=True)
    format: Mapped[str | None] = mapped_column(String(20), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ratio: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    creator: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rights: Mapped[str | None] = mapped_column(String(100), nullable=True)
    platforms: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组
    review_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_account: Mapped[str | None] = mapped_column(String(100), nullable=True)
    placements: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fatigue: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    user: Mapped["User"] = relationship(back_populates="materials")
    performance: Mapped[list["MaterialPerformance"]] = relationship(
        back_populates="material", cascade="all, delete-orphan"
    )
    
    # 辅助方法
    def get_project_ids(self) -> list[str]:
        """获取项目 ID 列表"""
        if not self.project_ids:
            return []
        return json.loads(self.project_ids)
    
    def set_project_ids(self, ids: list[str]) -> None:
        """设置项目 ID 列表"""
        self.project_ids = json.dumps(ids)
    
    def add_project(self, project_id: str) -> None:
        """添加项目关联"""
        ids = self.get_project_ids()
        if project_id not in ids:
            ids.append(project_id)
            self.set_project_ids(ids)
    
    def remove_project(self, project_id: str) -> None:
        """移除项目关联"""
        ids = self.get_project_ids()
        if project_id in ids:
            ids.remove(project_id)
            self.set_project_ids(ids)
    
    def get_campaign_ids(self) -> list[str]:
        """获取广告计划 ID 列表"""
        if not self.campaign_ids:
            return []
        return json.loads(self.campaign_ids)
    
    def set_campaign_ids(self, ids: list[str]) -> None:
        """设置广告计划 ID 列表"""
        self.campaign_ids = json.dumps(ids)
    
    def add_campaign(self, campaign_id: str) -> None:
        """添加广告计划关联"""
        ids = self.get_campaign_ids()
        if campaign_id not in ids:
            ids.append(campaign_id)
            self.set_campaign_ids(ids)
    
    def remove_campaign(self, campaign_id: str) -> None:
        """移除广告计划关联"""
        ids = self.get_campaign_ids()
        if campaign_id in ids:
            ids.remove(campaign_id)
            self.set_campaign_ids(ids)
