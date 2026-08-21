"""add user-triggered Meta Insights sync runs

Revision ID: 260821_01_meta_sync_runs
Revises: 260820_01_add_meta_facts
Create Date: 2026-08-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "260821_01_meta_sync_runs"
down_revision: Union[str, None] = "260820_01_add_meta_facts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "meta_insights_sync_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("connection_id", sa.String(length=36), nullable=False),
        sa.Column("account_id", sa.String(length=100), nullable=False),
        sa.Column("account_name", sa.String(length=255), nullable=True),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column("requested_since", sa.Date(), nullable=False),
        sa.Column("requested_until", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("rows_written", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["connection_id"], ["platform_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_meta_insights_sync_runs_account_started",
        "meta_insights_sync_runs",
        ["connection_id", "account_id", "level", "started_at"],
    )
    op.create_index(
        "ix_meta_insights_sync_runs_user_status",
        "meta_insights_sync_runs",
        ["user_id", "status"],
    )
    op.create_index(
        "uq_meta_insights_sync_runs_running_account_level",
        "meta_insights_sync_runs",
        ["connection_id", "account_id", "level"],
        unique=True,
        sqlite_where=sa.text("status = 'running'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_meta_insights_sync_runs_running_account_level",
        table_name="meta_insights_sync_runs",
    )
    op.drop_index(
        "ix_meta_insights_sync_runs_user_status",
        table_name="meta_insights_sync_runs",
    )
    op.drop_index(
        "ix_meta_insights_sync_runs_account_started",
        table_name="meta_insights_sync_runs",
    )
    op.drop_table("meta_insights_sync_runs")
