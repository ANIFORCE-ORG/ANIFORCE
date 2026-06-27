"""add agent_sessions table

Revision ID: 9b1c2d3e4f50
Revises: 6f2a9c1d4e88
Create Date: 2026-06-24 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9b1c2d3e4f50"
down_revision: Union[str, None] = "6f2a9c1d4e88"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_sessions",
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=80), nullable=False),
        sa.Column("status", sa.Enum("active", "archived", name="agentsessionstatus"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index(op.f("ix_agent_sessions_user_id"), "agent_sessions", ["user_id"], unique=False)
    op.create_index("idx_agent_sessions_user_updated", "agent_sessions", ["user_id", "updated_at"], unique=False)
    op.create_index("idx_agent_sessions_user_status", "agent_sessions", ["user_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_agent_sessions_user_status", table_name="agent_sessions")
    op.drop_index("idx_agent_sessions_user_updated", table_name="agent_sessions")
    op.drop_index(op.f("ix_agent_sessions_user_id"), table_name="agent_sessions")
    op.drop_table("agent_sessions")
