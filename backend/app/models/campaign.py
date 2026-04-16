"""广告投放模型"""
import uuid
import enum
import json
from datetime import datetime
from sqlalchemy import String, Float, DateTime, Enum, Text, Date, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base


class CampaignStatus(str, enum.Enum):
    """广告投放状态"""
    DRAFT = "draft"
    RUNNING = "running"
    REVIEW = "review"
    PAUSED = "paused"
    COMPLETED = "completed"


class Platform(str, enum.Enum):
    """投放平台"""
    TikTok = "TikTok"
    Google = "Google"
    Meta = "Meta"


class Campaign(Base):
    __tablename__ = "campaigns"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # 投放配置
    platform: Mapped[Platform] = mapped_column(Enum(Platform, native_enum=False), nullable=False, index=True)
    budget: Mapped[float] = mapped_column(Float, nullable=False)
    spent: Mapped[float] = mapped_column(Float, default=0.0)
    target_cpa: Mapped[float | None] = mapped_column(Float, nullable=True)  # 目标 CPA
    status: Mapped[CampaignStatus] = mapped_column(Enum(CampaignStatus, native_enum=False), default=CampaignStatus.DRAFT, index=True)
    pipeline_step: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)  # Pipeline 阶段

    # 学习和优化
    learning_phase: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 学习阶段
    auto_optimize_enabled: Mapped[bool] = mapped_column(Boolean, default=False)  # 自动优化开关
    optimization_rules: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组：优化规则
    
    # 素材管理
    material_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组
    
    # 投放周期
    start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    
    # 配置
    config: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    project: Mapped["Project"] = relationship(back_populates="campaigns")
    metrics: Mapped[list["Metric"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    
    # 辅助方法
    def get_material_ids(self) -> list[str]:
        """获取素材 ID 列表"""
        if not self.material_ids:
            return []
        return json.loads(self.material_ids)

    def set_material_ids(self, ids: list[str]) -> None:
        """设置素材 ID 列表"""
        self.material_ids = json.dumps(ids)

    def add_material(self, material_id: str) -> None:
        """添加素材"""
        ids = self.get_material_ids()
        if material_id not in ids:
            ids.append(material_id)
            self.set_material_ids(ids)

    def remove_material(self, material_id: str) -> None:
        """移除素材"""
        ids = self.get_material_ids()
        if material_id in ids:
            ids.remove(material_id)
            self.set_material_ids(ids)

    def get_optimization_rules(self) -> list[str]:
        """获取优化规则列表"""
        if not self.optimization_rules:
            return []
        return json.loads(self.optimization_rules)

    def set_optimization_rules(self, rules: list[str]) -> None:
        """设置优化规则列表"""
        self.optimization_rules = json.dumps(rules)
