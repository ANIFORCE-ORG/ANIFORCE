"""Backend-owned approval facts for interrupted Agent tool calls."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class AgentApproval(Base):
    __tablename__ = "agent_approvals"
    __table_args__ = (
        UniqueConstraint(
            "checkpoint_ref",
            "tool_call_id",
            name="uq_agent_approvals_checkpoint_tool_call",
        ),
        Index("idx_agent_approvals_user_status_expiry", "user_id", "status", "expires_at"),
        Index("idx_agent_approvals_run_status", "run_id", "status"),
        CheckConstraint(
            "status IN ('pending','resuming','resolved','rejected','expired','failed')",
            name="ck_agent_approvals_status",
        ),
    )

    approval_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    checkpoint_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    run_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("agent_runs.run_id", ondelete="CASCADE"),
        nullable=False,
    )
    tool_call_id: Mapped[str] = mapped_column(String(256), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    original_arguments_json: Mapped[str] = mapped_column(Text, nullable=False)
    edited_arguments_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    argument_diff_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
