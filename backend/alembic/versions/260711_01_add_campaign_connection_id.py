"""add missing campaign platform connection reference

Revision ID: 260711_01_campaign_connection
Revises: 260710_05_execution_fencing
Create Date: 2026-07-11 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "260711_01_campaign_connection"
down_revision: Union[str, None] = "260710_05_execution_fencing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def upgrade() -> None:
    inspector = _inspector()
    columns = {item["name"] for item in inspector.get_columns("campaigns")}
    if "connection_id" not in columns:
        op.add_column("campaigns", sa.Column("connection_id", sa.String(36), nullable=True))

    indexes = {item["name"] for item in _inspector().get_indexes("campaigns")}
    if "ix_campaigns_connection_id" not in indexes:
        op.create_index("ix_campaigns_connection_id", "campaigns", ["connection_id"], unique=False)


def downgrade() -> None:
    inspector = _inspector()
    indexes = {item["name"] for item in inspector.get_indexes("campaigns")}
    if "ix_campaigns_connection_id" in indexes:
        op.drop_index("ix_campaigns_connection_id", table_name="campaigns")

    columns = {item["name"] for item in _inspector().get_columns("campaigns")}
    if "connection_id" in columns:
        with op.batch_alter_table("campaigns") as batch_op:
            batch_op.drop_column("connection_id")
