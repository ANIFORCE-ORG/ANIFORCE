"""Backend-owned visible Agent message history."""

from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class AgentMessage(Base):
    """User-visible chat message fact source."""

    __tablename__ = "agent_messages"
    __table_args__ = (
        Index("idx_agent_messages_session_seq", "session_id", "sequence"),
        Index("idx_agent_messages_user_session", "user_id", "session_id"),
        UniqueConstraint("run_id", "role", name="uq_agent_messages_run_role"),
    )

    message_id: Mapped[str] = mapped_column(String(128), primary_key=True, default=lambda: f"msg_{uuid.uuid4().hex}")
    session_id: Mapped[str] = mapped_column(ForeignKey("agent_sessions.session_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    content_json: Mapped[str] = mapped_column(Text, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    run_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
