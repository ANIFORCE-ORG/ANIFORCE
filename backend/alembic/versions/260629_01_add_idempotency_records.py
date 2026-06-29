"""add idempotency records table

Revision ID: 260629_01_idempotency_records
Revises: 260624_02_agent_messages_runs
Create Date: 2026-06-29 19:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "260629_01_idempotency_records"
down_revision: Union[str, None] = "260624_02_agent_messages_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table: str) -> bool:
    rows = op.get_bind().exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchall()
    return bool(rows)


def upgrade() -> None:
    if _table_exists("idempotency_records"):
        return

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "key", name="uq_idempotency_user_key"),
    )
    op.create_index(op.f("ix_idempotency_records_user_id"), "idempotency_records", ["user_id"], unique=False)
    op.create_index(op.f("ix_idempotency_records_key"), "idempotency_records", ["key"], unique=False)


def downgrade() -> None:
    if _table_exists("idempotency_records"):
        op.drop_index(op.f("ix_idempotency_records_key"), table_name="idempotency_records")
        op.drop_index(op.f("ix_idempotency_records_user_id"), table_name="idempotency_records")
        op.drop_table("idempotency_records")
