"""add persistent agent run events

Revision ID: 260710_02_run_events
Revises: 260710_01_run_checkpoint
Create Date: 2026-07-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "260710_02_run_events"
down_revision: Union[str, None] = "260710_01_run_checkpoint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


def _column_exists(table: str, column: str) -> bool:
    return column in {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if not _column_exists("agent_runs", "last_event_sequence"):
        op.add_column(
            "agent_runs",
            sa.Column("last_event_sequence", sa.Integer(), nullable=False, server_default="0"),
        )
    if not _column_exists("agent_runs", "terminal_event_id"):
        op.add_column("agent_runs", sa.Column("terminal_event_id", sa.String(length=128), nullable=True))
        op.create_index("uq_agent_runs_terminal_event_id", "agent_runs", ["terminal_event_id"], unique=True)

    if not _table_exists("agent_run_events"):
        op.create_table(
            "agent_run_events",
            sa.Column("id", sa.String(length=128), nullable=False),
            sa.Column("run_id", sa.String(length=128), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("event_type", sa.String(length=64), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("is_terminal", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["run_id"], ["agent_runs.run_id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("run_id", "sequence", name="uq_agent_run_events_sequence"),
        )
        op.create_index(
            "idx_agent_run_events_run_created",
            "agent_run_events",
            ["run_id", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    if _table_exists("agent_run_events"):
        op.drop_table("agent_run_events")
    if _column_exists("agent_runs", "terminal_event_id"):
        op.drop_index("uq_agent_runs_terminal_event_id", table_name="agent_runs")
        with op.batch_alter_table("agent_runs") as batch_op:
            batch_op.drop_column("terminal_event_id")
    if _column_exists("agent_runs", "last_event_sequence"):
        with op.batch_alter_table("agent_runs") as batch_op:
            batch_op.drop_column("last_event_sequence")
