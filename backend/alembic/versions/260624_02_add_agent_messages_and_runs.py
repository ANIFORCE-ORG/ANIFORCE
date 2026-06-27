"""add agent messages and runs

Revision ID: 260624_02_agent_messages_runs
Revises: 260624_01_material_metadata
Create Date: 2026-06-24 21:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "260624_02_agent_messages_runs"
down_revision: Union[str, None] = "260624_01_material_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table: str) -> bool:
    rows = op.get_bind().exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchall()
    return bool(rows)


def upgrade() -> None:
    if not _table_exists("agent_messages"):
        op.create_table(
            "agent_messages",
            sa.Column("message_id", sa.String(length=128), nullable=False),
            sa.Column("session_id", sa.String(length=128), nullable=False),
            sa.Column("user_id", sa.String(length=128), nullable=False),
            sa.Column("role", sa.String(length=32), nullable=False),
            sa.Column("content_json", sa.Text(), nullable=False),
            sa.Column("run_id", sa.String(length=128), nullable=True),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["agent_sessions.session_id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("message_id"),
        )
        op.create_index("idx_agent_messages_session_seq", "agent_messages", ["session_id", "sequence"], unique=False)
        op.create_index("idx_agent_messages_user_session", "agent_messages", ["user_id", "session_id"], unique=False)
        op.create_index(op.f("ix_agent_messages_user_id"), "agent_messages", ["user_id"], unique=False)
        op.create_index(op.f("ix_agent_messages_run_id"), "agent_messages", ["run_id"], unique=False)

    if not _table_exists("agent_runs"):
        op.create_table(
            "agent_runs",
            sa.Column("run_id", sa.String(length=128), nullable=False),
            sa.Column("session_id", sa.String(length=128), nullable=False),
            sa.Column("user_id", sa.String(length=128), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("input_text", sa.Text(), nullable=False),
            sa.Column("trace_id", sa.String(length=128), nullable=True),
            sa.Column("idempotency_key", sa.String(length=128), nullable=True),
            sa.Column("usage_json", sa.Text(), nullable=True),
            sa.Column("error_json", sa.Text(), nullable=True),
            sa.Column("pending_approval_json", sa.Text(), nullable=True),
            sa.Column("run_state_json", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("run_id"),
            sa.UniqueConstraint("user_id", "session_id", "idempotency_key", name="uq_agent_runs_idempotency"),
        )
        op.create_index("idx_agent_runs_session_started", "agent_runs", ["session_id", "started_at"], unique=False)
        op.create_index("idx_agent_runs_user_session_status", "agent_runs", ["user_id", "session_id", "status"], unique=False)
        op.create_index(op.f("ix_agent_runs_session_id"), "agent_runs", ["session_id"], unique=False)
        op.create_index(op.f("ix_agent_runs_user_id"), "agent_runs", ["user_id"], unique=False)


def downgrade() -> None:
    if _table_exists("agent_runs"):
        op.drop_table("agent_runs")
    if _table_exists("agent_messages"):
        op.drop_table("agent_messages")
