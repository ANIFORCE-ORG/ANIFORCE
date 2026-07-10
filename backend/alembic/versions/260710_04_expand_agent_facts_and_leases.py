"""expand agent facts, execution leases, and recoverable artifacts

Revision ID: 260710_04_agent_facts
Revises: 260710_03_approvals
Create Date: 2026-07-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "260710_04_agent_facts"
down_revision: Union[str, None] = "260710_03_approvals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table: str) -> set[str]:
    return {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    run_columns = _columns("agent_runs")
    additions = {
        "version": sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        "lease_owner": sa.Column("lease_owner", sa.String(length=128), nullable=True),
        "lease_expires_at": sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        "heartbeat_at": sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
        "runtime_started_at": sa.Column("runtime_started_at", sa.DateTime(), nullable=True),
        "cancel_requested_at": sa.Column("cancel_requested_at", sa.DateTime(), nullable=True),
        "retryable": sa.Column("retryable", sa.Boolean(), nullable=True),
    }
    for name, column in additions.items():
        if name not in run_columns:
            op.add_column("agent_runs", column)
    op.create_index("idx_agent_runs_status_lease", "agent_runs", ["status", "lease_expires_at"], unique=False)

    message_columns = _columns("agent_messages")
    if "status" not in message_columns:
        op.add_column("agent_messages", sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"))
    if "error_code" not in message_columns:
        op.add_column("agent_messages", sa.Column("error_code", sa.String(length=64), nullable=True))
    if "completed_at" not in message_columns:
        op.add_column("agent_messages", sa.Column("completed_at", sa.DateTime(), nullable=True))
    op.create_index("uq_agent_messages_run_role", "agent_messages", ["run_id", "role"], unique=True)

    op.create_table(
        "agent_tool_calls",
        sa.Column("tool_call_id", sa.String(length=256), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("tool_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("arguments_json", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error_json", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=256), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tool_call_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_agent_tool_calls_idempotency_key"),
    )
    op.create_index("idx_agent_tool_calls_run_status", "agent_tool_calls", ["run_id", "status"], unique=False)

    op.create_table(
        "agent_artifacts",
        sa.Column("artifact_id", sa.String(length=128), nullable=False),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("source_tool_call_id", sa.String(length=256), nullable=True),
        sa.Column("surface", sa.String(length=128), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("entity_versions_json", sa.Text(), nullable=True),
        sa.Column("supersedes_artifact_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.run_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["agent_sessions.session_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("artifact_id"),
    )
    op.create_index("idx_agent_artifacts_session_updated", "agent_artifacts", ["session_id", "updated_at"], unique=False)
    op.create_index("idx_agent_artifacts_run_status", "agent_artifacts", ["run_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_table("agent_artifacts")
    op.drop_table("agent_tool_calls")
    op.drop_index("uq_agent_messages_run_role", table_name="agent_messages")
    with op.batch_alter_table("agent_messages") as batch_op:
        batch_op.drop_column("completed_at")
        batch_op.drop_column("error_code")
        batch_op.drop_column("status")
    op.drop_index("idx_agent_runs_status_lease", table_name="agent_runs")
    with op.batch_alter_table("agent_runs") as batch_op:
        for name in (
            "retryable", "cancel_requested_at", "runtime_started_at", "heartbeat_at",
            "lease_expires_at", "lease_owner", "version",
        ):
            batch_op.drop_column(name)
