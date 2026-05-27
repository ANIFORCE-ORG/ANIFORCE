"""组织成员模型"""
import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class OrganizationMember(Base):
    """组织成员模型"""
    __tablename__ = "organization_members"
    
    # 主键
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 外键
    organization_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("organizations.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    # 角色
    role: Mapped[str] = mapped_column(
        String(20), 
        default="member", 
        nullable=False
    )  # 'admin', 'member'
    
    # 邀请信息
    invited_by: Mapped[Optional[str]] = mapped_column(
        String(36), 
        ForeignKey("users.id", ondelete="SET NULL"), 
        nullable=True
    )
    
    # 状态
    status: Mapped[str] = mapped_column(
        String(20), 
        default="active", 
        nullable=False,
        index=True
    )  # 'active', 'inactive'
    
    # 时间戳
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关系
    organization: Mapped["Organization"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    inviter: Mapped[Optional["User"]] = relationship(foreign_keys=[invited_by])
    
    # 约束
    __table_args__ = (
        UniqueConstraint('organization_id', 'user_id', name='uq_org_user'),
    )
