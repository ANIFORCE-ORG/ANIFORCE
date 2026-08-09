"""add material platform assets and sync runs

Revision ID: 260728_01_material_sync
Revises: 260713_02_ad_set_evidence
Create Date: 2026-07-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "260728_01_material_sync"
down_revision: Union[str, None] = "260713_02_ad_set_evidence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "material_sync_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("connection_id", sa.String(length=36), nullable=False),
        sa.Column("ad_account_id", sa.String(length=100), nullable=False),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("discovered_count", sa.Integer(), nullable=False),
        sa.Column("created_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["connection_id"], ["platform_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_material_sync_runs_connection_id", "material_sync_runs", ["connection_id"])
    op.create_index("ix_material_sync_runs_user_id", "material_sync_runs", ["user_id"])
    op.create_index(
        "ix_material_sync_runs_account_started",
        "material_sync_runs",
        ["connection_id", "ad_account_id", "started_at"],
    )
    op.create_index(
        "ix_material_sync_runs_user_status",
        "material_sync_runs",
        ["user_id", "status"],
    )

    op.create_table(
        "material_platform_assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("material_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("connection_id", sa.String(length=36), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("ad_account_id", sa.String(length=100), nullable=False),
        sa.Column("asset_type", sa.String(length=20), nullable=False),
        sa.Column("external_asset_id", sa.String(length=255), nullable=False),
        sa.Column("image_hash", sa.String(length=128), nullable=True),
        sa.Column("remote_name", sa.String(length=255), nullable=True),
        sa.Column("remote_status", sa.String(length=50), nullable=True),
        sa.Column("remote_url", sa.Text(), nullable=True),
        sa.Column("remote_thumbnail_url", sa.Text(), nullable=True),
        sa.Column("remote_created_at", sa.DateTime(), nullable=True),
        sa.Column("remote_updated_at", sa.DateTime(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["platform_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "connection_id",
            "ad_account_id",
            "asset_type",
            "external_asset_id",
            name="uq_material_platform_asset_identity",
        ),
    )
    op.create_index("ix_material_platform_assets_connection_id", "material_platform_assets", ["connection_id"])
    op.create_index("ix_material_platform_assets_material_id", "material_platform_assets", ["material_id"])
    op.create_index("ix_material_platform_assets_user_id", "material_platform_assets", ["user_id"])
    op.create_index(
        "ix_material_platform_assets_account",
        "material_platform_assets",
        ["connection_id", "ad_account_id"],
    )
    op.create_index(
        "ix_material_platform_assets_dedupe",
        "material_platform_assets",
        ["user_id", "platform", "asset_type", "image_hash"],
    )


def downgrade() -> None:
    op.drop_index("ix_material_platform_assets_dedupe", table_name="material_platform_assets")
    op.drop_index("ix_material_platform_assets_account", table_name="material_platform_assets")
    op.drop_index("ix_material_platform_assets_user_id", table_name="material_platform_assets")
    op.drop_index("ix_material_platform_assets_material_id", table_name="material_platform_assets")
    op.drop_index("ix_material_platform_assets_connection_id", table_name="material_platform_assets")
    op.drop_table("material_platform_assets")

    op.drop_index("ix_material_sync_runs_user_status", table_name="material_sync_runs")
    op.drop_index("ix_material_sync_runs_account_started", table_name="material_sync_runs")
    op.drop_index("ix_material_sync_runs_user_id", table_name="material_sync_runs")
    op.drop_index("ix_material_sync_runs_connection_id", table_name="material_sync_runs")
    op.drop_table("material_sync_runs")
