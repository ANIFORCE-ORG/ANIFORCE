"""add backend-owned agent approvals

Revision ID: 260710_03_approvals
Revises: 260710_02_run_events
Create Date: 2026-07-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "260710_03_approvals"
down_revision: Union[str, None] = "260710_02_run_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("agent_approvals"):
        return
    op.create_table(
        "agent_approvals",
        sa.Column("approval_id", sa.String(length=128), nullable=False),
        sa.Column("checkpoint_ref", sa.String(length=128), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("tool_call_id", sa.String(length=256), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=True),
        sa.Column("original_arguments_json", sa.Text(), nullable=False),
        sa.Column("edited_arguments_json", sa.Text(), nullable=True),
        sa.Column("argument_diff_json", sa.Text(), nullable=True),
        sa.Column("rejection_message", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending','resuming','resolved','rejected','expired','failed')",
            name="ck_agent_approvals_status",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("approval_id"),
        sa.UniqueConstraint(
            "checkpoint_ref",
            "tool_call_id",
            name="uq_agent_approvals_checkpoint_tool_call",
        ),
    )
    op.create_index(
        "idx_agent_approvals_user_status_expiry",
        "agent_approvals",
        ["user_id", "status", "expires_at"],
        unique=False,
    )
    op.create_index(
        "idx_agent_approvals_run_status",
        "agent_approvals",
        ["run_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("agent_approvals"):
        op.drop_table("agent_approvals")
