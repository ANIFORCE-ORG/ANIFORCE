"""联系信息模型"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.config.database import Base


class ContactInfo(Base):
    __tablename__ = "contact_info"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    company: Mapped[str] = mapped_column(String(200), nullable=False)
    contact: Mapped[str] = mapped_column(String(200), nullable=False)  # 邮箱或电话
    message: Mapped[str | None] = mapped_column(Text, nullable=True)  # 可选的留言
    source: Mapped[str | None] = mapped_column(String(50), nullable=True, default="website")  # 来源
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending, contacted, completed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
