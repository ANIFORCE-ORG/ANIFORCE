"""Database lease enforcing one active execution per Agent session."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class AgentSessionLease(Base):
    __tablename__ = "agent_session_leases"
    __table_args__ = (Index("idx_agent_session_leases_expiry", "lease_expires_at"),)

    session_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("agent_sessions.session_id", ondelete="CASCADE"), primary_key=True
    )
    run_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("agent_runs.run_id", ondelete="CASCADE"), nullable=False, unique=True
    )
    lease_owner: Mapped[str] = mapped_column(String(128), nullable=False)
    lease_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
