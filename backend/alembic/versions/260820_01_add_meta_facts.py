"""add single-table Meta daily facts store

Revision ID: 260820_01_add_meta_facts
Revises: 260806_01_material_sync_connection_set_null
Create Date: 2026-08-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "260820_01_add_meta_facts"
down_revision: Union[str, None] = "260806_01_material_sync_connection_set_null"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "meta_facts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("connection_id", sa.String(length=36), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("account_id", sa.String(length=100), nullable=False),
        sa.Column("account_name", sa.String(length=255), nullable=True),
        sa.Column("business_manager_id", sa.String(length=100), nullable=True),
        sa.Column("entity_id", sa.String(length=100), nullable=False),
        sa.Column("entity_name", sa.String(length=255), nullable=True),
        sa.Column("parent_entity_id", sa.String(length=100), nullable=True),
        sa.Column("parent_entity_name", sa.String(length=255), nullable=True),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("date_stop", sa.Date(), nullable=True),
        sa.Column("attribution_setting", sa.String(length=100), nullable=False),
        sa.Column("account_currency", sa.String(length=12), nullable=True),
        sa.Column("account_timezone", sa.String(length=80), nullable=True),
        sa.Column("objective", sa.String(length=100), nullable=True),
        sa.Column("optimization_goal", sa.String(length=100), nullable=True),
        sa.Column("impressions", sa.Integer(), nullable=True),
        sa.Column("reach", sa.Integer(), nullable=True),
        sa.Column("frequency", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("clicks", sa.Integer(), nullable=True),
        sa.Column("inline_link_clicks", sa.Integer(), nullable=True),
        sa.Column("spend", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column("ctr", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("cpc", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("cpm", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("actions_json", sa.JSON(), nullable=True),
        sa.Column("action_values_json", sa.JSON(), nullable=True),
        sa.Column("cost_per_action_type_json", sa.JSON(), nullable=True),
        sa.Column("conversion_values_json", sa.JSON(), nullable=True),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("sync_run_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["platform_connections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "connection_id",
            "level",
            "entity_id",
            "metric_date",
            "attribution_setting",
            name="uq_meta_facts_identity",
        ),
    )
    op.create_index("ix_meta_facts_connection_date", "meta_facts", ["connection_id", "metric_date"])
    op.create_index("ix_meta_facts_account_level_date", "meta_facts", ["account_id", "level", "metric_date"])
    op.create_index("ix_meta_facts_entity", "meta_facts", ["level", "entity_id"])


def downgrade() -> None:
    op.drop_index("ix_meta_facts_entity", table_name="meta_facts")
    op.drop_index("ix_meta_facts_account_level_date", table_name="meta_facts")
    op.drop_index("ix_meta_facts_connection_date", table_name="meta_facts")
    op.drop_table("meta_facts")
