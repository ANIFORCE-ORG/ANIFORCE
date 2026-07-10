"""Backend-owned Agent run execution log."""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class AgentRun(Base):
    """One user turn execution record."""

    __tablename__ = "agent_runs"
    __table_args__ = (
        Index("idx_agent_runs_session_started", "session_id", "started_at"),
        Index("idx_agent_runs_user_session_status", "user_id", "session_id", "status"),
        UniqueConstraint("user_id", "session_id", "idempotency_key", name="uq_agent_runs_idempotency"),
    )

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    usage_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    pending_approval_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_state_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    checkpoint_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_event_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    terminal_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
