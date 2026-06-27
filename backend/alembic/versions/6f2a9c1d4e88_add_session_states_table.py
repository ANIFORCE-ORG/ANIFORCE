"""add session_states table

Revision ID: 6f2a9c1d4e88
Revises: 4951fcc09d73
Create Date: 2026-06-24 19:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6f2a9c1d4e88"
down_revision: Union[str, None] = "4951fcc09d73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_states",
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("linked_entities_json", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("pending_actions_json", sa.Text(), nullable=False),
        sa.Column("changelog_json", sa.Text(), nullable=False),
        sa.Column("ui_snapshot_json", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_error_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index(op.f("ix_session_states_user_id"), "session_states", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_session_states_user_id"), table_name="session_states")
    op.drop_table("session_states")
