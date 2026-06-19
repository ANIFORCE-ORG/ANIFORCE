"""用户模型"""
import uuid
import enum
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base

if TYPE_CHECKING:
    from app.models.organization import Organization


class SystemRole(str, enum.Enum):
    """系统角色枚举"""
    ADMIN = "ADMIN"  # 管理员
    USER = "USER"    # 普通用户


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    system_role: Mapped[SystemRole] = mapped_column(Enum(SystemRole), nullable=False, default=SystemRole.USER)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    projects: Mapped[list["Project"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    materials: Mapped[list["Material"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    platform_connections: Mapped[list["PlatformConnection"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    owned_organizations: Mapped[list["Organization"]] = relationship(back_populates="owner", foreign_keys="Organization.owner_id")
