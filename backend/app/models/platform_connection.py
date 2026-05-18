"""平台连接模型"""
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base


class PlatformConnection(Base):
    """平台连接模型 - 存储用户的广告平台连接信息"""
    __tablename__ = "platform_connections"
    
    # 主键
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 外键
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 平台信息
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 'TikTok', 'Google', 'Meta'
    
    # 账号信息
    account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    account_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    account_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # OAuth 令牌
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_type: Mapped[str] = mapped_column(String(50), default="Bearer", nullable=False)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 权限范围（存储为 JSON 数组，因为 SQLite 不支持 ARRAY 类型）
    scopes: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # 状态管理
    status: Mapped[str] = mapped_column(
        String(20), 
        default="active", 
        nullable=False
    )  # 'unauthorized', 'active', 'expired', 'revoked'
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 元数据（使用 extra_data 避免与 SQLAlchemy 的 metadata 属性冲突）
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关系
    user: Mapped["User"] = relationship(back_populates="platform_connections")
    
    def __repr__(self):
        return f"<PlatformConnection(id={self.id}, user_id={self.user_id}, platform={self.platform}, account_id={self.account_id})>"
