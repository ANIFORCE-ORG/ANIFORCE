"""Backend-owned Agent product session metadata."""

from datetime import datetime
import enum

from sqlalchemy import DateTime, Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class AgentSessionStatus(str, enum.Enum):
    """Product session lifecycle status."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class AgentSession(Base):
    """Product session fact source owned by backend."""

    __tablename__ = "agent_sessions"
    __table_args__ = (
        Index("idx_agent_sessions_user_updated", "user_id", "updated_at"),
        Index("idx_agent_sessions_user_status", "user_id", "status"),
    )

    session_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[AgentSessionStatus] = mapped_column(
        Enum(AgentSessionStatus, values_callable=lambda enum_cls: [item.value for item in enum_cls]),
        nullable=False,
        default=AgentSessionStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
