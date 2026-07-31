"""add material storage identity and per-asset sync results

Revision ID: 260728_02_sync_details
Revises: 260728_01_material_sync
Create Date: 2026-07-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "260728_02_sync_details"
down_revision: Union[str, None] = "260728_01_material_sync"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("materials", sa.Column("storage_object_key", sa.Text(), nullable=True))
    op.add_column("materials", sa.Column("mime_type", sa.String(length=100), nullable=True))
    op.add_column("materials", sa.Column("checksum_sha256", sa.String(length=64), nullable=True))
    op.create_index(
        "ix_materials_user_checksum",
        "materials",
        ["user_id", "checksum_sha256"],
    )

    op.add_column(
        "material_sync_runs",
        sa.Column("asset_types", sa.Text(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "material_sync_runs",
        sa.Column("reused_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "material_sync_run_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("asset_type", sa.String(length=20), nullable=False),
        sa.Column("external_asset_id", sa.String(length=255), nullable=False),
        sa.Column("remote_name", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("material_id", sa.String(length=36), nullable=True),
        sa.Column("platform_asset_id", sa.String(length=36), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["platform_asset_id"],
            ["material_platform_assets.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["material_sync_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_material_sync_run_items_run_id", "material_sync_run_items", ["run_id"]
    )
    op.create_index(
        "ix_material_sync_run_items_material_id",
        "material_sync_run_items",
        ["material_id"],
    )
    op.create_index(
        "ix_material_sync_run_items_platform_asset_id",
        "material_sync_run_items",
        ["platform_asset_id"],
    )
    op.create_index(
        "ix_material_sync_run_items_run_action",
        "material_sync_run_items",
        ["run_id", "action"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_material_sync_run_items_run_action", table_name="material_sync_run_items"
    )
    op.drop_index(
        "ix_material_sync_run_items_platform_asset_id",
        table_name="material_sync_run_items",
    )
    op.drop_index(
        "ix_material_sync_run_items_material_id", table_name="material_sync_run_items"
    )
    op.drop_index(
        "ix_material_sync_run_items_run_id", table_name="material_sync_run_items"
    )
    op.drop_table("material_sync_run_items")

    op.drop_column("material_sync_runs", "reused_count")
    op.drop_column("material_sync_runs", "asset_types")

    op.drop_index("ix_materials_user_checksum", table_name="materials")
    op.drop_column("materials", "checksum_sha256")
    op.drop_column("materials", "mime_type")
    op.drop_column("materials", "storage_object_key")
