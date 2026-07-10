"""add session leases and resumable execution commands

Revision ID: 260710_05_execution_fencing
Revises: 260710_04_agent_facts
Create Date: 2026-07-10 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "260710_05_execution_fencing"
down_revision: Union[str, None] = "260710_04_agent_facts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("execution_kind", sa.String(32), nullable=False, server_default="initial"))
    op.add_column("agent_runs", sa.Column("resume_payload_json", sa.Text(), nullable=True))
    op.add_column("agent_runs", sa.Column("error_code", sa.String(64), nullable=True))
    op.create_index("idx_agent_runs_session_execution", "agent_runs", ["session_id", "status", "lease_expires_at"], unique=False)

    op.add_column("agent_approvals", sa.Column("preconditions_json", sa.Text(), nullable=True))
    op.add_column("agent_approvals", sa.Column("claimed_by", sa.String(128), nullable=True))
    op.add_column("agent_approvals", sa.Column("resolved_by", sa.String(128), nullable=True))

    op.create_table(
        "agent_session_leases",
        sa.Column("session_id", sa.String(128), nullable=False),
        sa.Column("run_id", sa.String(128), nullable=False),
        sa.Column("lease_owner", sa.String(128), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.run_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["agent_sessions.session_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id"),
        sa.UniqueConstraint("run_id", name="uq_agent_session_leases_run_id"),
    )
    op.create_index("idx_agent_session_leases_expiry", "agent_session_leases", ["lease_expires_at"], unique=False)


def downgrade() -> None:
    op.drop_table("agent_session_leases")
    with op.batch_alter_table("agent_approvals") as batch_op:
        batch_op.drop_column("resolved_by")
        batch_op.drop_column("claimed_by")
        batch_op.drop_column("preconditions_json")
    op.drop_index("idx_agent_runs_session_execution", table_name="agent_runs")
    with op.batch_alter_table("agent_runs") as batch_op:
        batch_op.drop_column("error_code")
        batch_op.drop_column("resume_payload_json")
        batch_op.drop_column("execution_kind")
