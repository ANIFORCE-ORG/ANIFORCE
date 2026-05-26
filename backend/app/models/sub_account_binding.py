"""子账号绑定模型"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base


class SubAccountBinding(Base):
    """子账号绑定模型 - 管理 Google 母账号和子账号的关系"""
    __tablename__ = "sub_account_bindings"
    
    # 主键
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 外键 - 关联到 platform_connections 表
    parent_connection_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("platform_connections.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    # 子账号信息
    sub_account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # 状态
    status: Mapped[str] = mapped_column(
        String(20), 
        default="active", 
        nullable=False
    )  # 'active', 'inactive'
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关系
    parent_connection: Mapped["PlatformConnection"] = relationship(back_populates="sub_account_bindings")
    
    def __repr__(self):
        return f"<SubAccountBinding(id={self.id}, parent_connection_id={self.parent_connection_id}, customer_id={self.customer_id})>"
