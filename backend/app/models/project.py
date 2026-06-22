"""项目模型"""
import uuid
import enum
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
    """项目模型 - 对应 Meta Campaign 层级"""
    __tablename__ = "projects"
    
    # 主键和外键
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="项目唯一标识")
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属用户ID")
    
    # 基本信息
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="项目名称，对应前端的项目名称字段")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="项目描述")
    
    # 投放配置（对应前端表单字段）
    product: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="产品名称，例如：休闲消除手游")
    
    # 项目信息（原有字段）
    game_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="游戏类型")
    target_market: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="目标市场")
    tags: Mapped[str | None] = mapped_column(Text, nullable=True, comment="标签，JSON数组格式")
    
    # 预算和状态
    total_budget: Mapped[float] = mapped_column(Float, nullable=False, comment="总预算金额")
    spent: Mapped[float] = mapped_column(Float, default=0.0, comment="已花费金额")
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.ACTIVE, index=True, comment="项目状态: active, paused, completed")
    
    # 负责人和时间
    manager: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="项目负责人")
    start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True, comment="项目开始日期")
    end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True, comment="项目结束日期")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系
    user: Mapped["User"] = relationship(back_populates="projects")
    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="project", cascade="all, delete-orphan")
