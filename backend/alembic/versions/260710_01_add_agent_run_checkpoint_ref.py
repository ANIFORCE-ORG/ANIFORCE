"""add agent run checkpoint reference

Revision ID: 260710_01_run_checkpoint
Revises: 260629_01_idempotency_records
Create Date: 2026-07-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "260710_01_run_checkpoint"
down_revision: Union[str, None] = "260629_01_idempotency_records"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column in {item["name"] for item in inspector.get_columns(table)}


def upgrade() -> None:
    if not _column_exists("agent_runs", "checkpoint_ref"):
        op.add_column("agent_runs", sa.Column("checkpoint_ref", sa.String(length=128), nullable=True))


def downgrade() -> None:
    if _column_exists("agent_runs", "checkpoint_ref"):
        with op.batch_alter_table("agent_runs") as batch_op:
            batch_op.drop_column("checkpoint_ref")
