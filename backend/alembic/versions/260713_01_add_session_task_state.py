"""add structured Agent session task state

Revision ID: 260713_01_session_task_state
Revises: 260711_01_campaign_connection
Create Date: 2026-07-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "260713_01_session_task_state"
down_revision: Union[str, None] = "260711_01_campaign_connection"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "session_states",
        sa.Column("task_state_json", sa.Text(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("session_states", "task_state_json")
