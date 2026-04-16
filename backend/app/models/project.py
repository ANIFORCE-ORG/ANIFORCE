"""项目模型"""
import uuid
import enum
import json
from datetime import datetime
from sqlalchemy import String, Float, DateTime, Enum, Text, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base


class ProjectStatus(str, enum.Enum):
    """项目状态"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class Project(Base):
    __tablename__ = "projects"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # 项目信息
    game_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    product_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 产品类型（与 game_type 合并使用）
    target_market: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组：目标地区
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组

    # 预算和状态
    total_budget: Mapped[float] = mapped_column(Float, nullable=False)
    spent: Mapped[float] = mapped_column(Float, default=0.0)
    target_roi: Mapped[float | None] = mapped_column(Float, nullable=True)  # 目标 ROI
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.ACTIVE, index=True)
    
    # 负责人和时间
    manager: Mapped[str | None] = mapped_column(String(100), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    user: Mapped["User"] = relationship(back_populates="projects")
    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="project", cascade="all, delete-orphan")

    # 辅助方法
    def get_region(self) -> list[str]:
        """获取目标地区列表"""
        if not self.region:
            return []
        return json.loads(self.region)

    def set_region(self, regions: list[str]) -> None:
        """设置目标地区列表"""
        self.region = json.dumps(regions)

    def get_tags(self) -> list[str]:
        """获取标签列表"""
        if not self.tags:
            return []
        return json.loads(self.tags)

    def set_tags(self, tags: list[str]) -> None:
        """设置标签列表"""
        self.tags = json.dumps(tags)
