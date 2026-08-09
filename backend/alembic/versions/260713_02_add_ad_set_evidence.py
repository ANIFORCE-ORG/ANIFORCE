"""add ad set and material performance evidence

Revision ID: 260713_02_ad_set_evidence
Revises: 260713_01_session_task_state
Create Date: 2026-07-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "260713_02_ad_set_evidence"
down_revision: Union[str, None] = "260713_01_session_task_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ad_sets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("platform_ad_set_id", sa.String(length=100), nullable=True),
        sa.Column("audience", sa.Text(), nullable=True),
        sa.Column("placements", sa.Text(), nullable=True),
        sa.Column("optimization_goal", sa.String(length=100), nullable=True),
        sa.Column("bid_strategy", sa.String(length=100), nullable=True),
        sa.Column("daily_budget", sa.Float(), nullable=False),
        sa.Column("spent", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=9), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ad_sets_campaign_id", "ad_sets", ["campaign_id"])
    op.create_index("ix_ad_sets_platform_ad_set_id", "ad_sets", ["platform_ad_set_id"])
    op.create_index("ix_ad_sets_status", "ad_sets", ["status"])

    op.create_table(
        "ad_set_metrics",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("ad_set_id", sa.String(length=36), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False),
        sa.Column("conversions", sa.Integer(), nullable=False),
        sa.Column("installs", sa.Integer(), nullable=False),
        sa.Column("spend", sa.Float(), nullable=False),
        sa.Column("revenue", sa.Float(), nullable=False),
        sa.Column("ctr", sa.Float(), nullable=False),
        sa.Column("cvr", sa.Float(), nullable=False),
        sa.Column("cpa", sa.Float(), nullable=False),
        sa.Column("cpi", sa.Float(), nullable=False),
        sa.Column("roi", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["ad_set_id"], ["ad_sets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ad_set_metrics_ad_set_id", "ad_set_metrics", ["ad_set_id"])
    op.create_index("ix_ad_set_metrics_timestamp", "ad_set_metrics", ["timestamp"])

    op.create_table(
        "material_performance",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("material_id", sa.String(length=36), nullable=False),
        sa.Column("ad_set_id", sa.String(length=36), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False),
        sa.Column("conversions", sa.Integer(), nullable=False),
        sa.Column("installs", sa.Integer(), nullable=False),
        sa.Column("spend", sa.Float(), nullable=False),
        sa.Column("revenue", sa.Float(), nullable=False),
        sa.Column("ctr", sa.Float(), nullable=False),
        sa.Column("cvr", sa.Float(), nullable=False),
        sa.Column("cpi", sa.Float(), nullable=False),
        sa.Column("roi", sa.Float(), nullable=False),
        sa.Column("frequency", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["ad_set_id"], ["ad_sets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_material_performance_ad_set_id", "material_performance", ["ad_set_id"])
    op.create_index("ix_material_performance_material_id", "material_performance", ["material_id"])
    op.create_index("ix_material_performance_timestamp", "material_performance", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_material_performance_timestamp", table_name="material_performance")
    op.drop_index("ix_material_performance_material_id", table_name="material_performance")
    op.drop_index("ix_material_performance_ad_set_id", table_name="material_performance")
    op.drop_table("material_performance")
    op.drop_index("ix_ad_set_metrics_timestamp", table_name="ad_set_metrics")
    op.drop_index("ix_ad_set_metrics_ad_set_id", table_name="ad_set_metrics")
    op.drop_table("ad_set_metrics")
    op.drop_index("ix_ad_sets_status", table_name="ad_sets")
    op.drop_index("ix_ad_sets_platform_ad_set_id", table_name="ad_sets")
    op.drop_index("ix_ad_sets_campaign_id", table_name="ad_sets")
    op.drop_table("ad_sets")
