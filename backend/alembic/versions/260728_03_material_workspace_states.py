"""add bidirectional material workspace state fields

Revision ID: 260728_03_material_workspace_states
Revises: 260728_02_sync_details
Create Date: 2026-07-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "260728_03_material_workspace_states"
down_revision: Union[str, None] = "260728_02_sync_details"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    return any(item["name"] == column for item in sa.inspect(op.get_bind()).get_columns(table))


def _has_index(table: str, index_name: str) -> bool:
    return any(item["name"] == index_name for item in sa.inspect(op.get_bind()).get_indexes(table))


def _add_column(table: str, column: sa.Column) -> None:
    if not _has_column(table, column.name):
        op.add_column(table, column)


def _add_index(name: str, table: str, columns: list[str]) -> None:
    if not _has_index(table, name):
        op.create_index(name, table, columns)


def upgrade() -> None:
    _add_column("materials", sa.Column("original_filename", sa.String(length=255), nullable=True))
    _add_column("materials", sa.Column("lifecycle_status", sa.String(length=20), nullable=False, server_default="active"))
    _add_column("materials", sa.Column("processing_status", sa.String(length=20), nullable=False, server_default="ready"))
    _add_column("materials", sa.Column("archived_at", sa.DateTime(), nullable=True))
    _add_column("materials", sa.Column("updated_at", sa.DateTime(), nullable=True))
    if _has_column("materials", "created_at"):
        op.execute("UPDATE materials SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)")
    else:
        op.execute("UPDATE materials SET updated_at = CURRENT_TIMESTAMP")
    _add_index("ix_materials_user_lifecycle", "materials", ["user_id", "lifecycle_status"])
    _add_index("ix_materials_user_processing", "materials", ["user_id", "processing_status"])

    _add_column("material_platform_assets", sa.Column("created_via", sa.String(length=20), nullable=False, server_default="import"))
    _add_column("material_platform_assets", sa.Column("normalized_status", sa.String(length=20), nullable=False, server_default="unknown"))
    _add_column("material_platform_assets", sa.Column("last_verified_at", sa.DateTime(), nullable=True))
    _add_column("material_platform_assets", sa.Column("last_error", sa.Text(), nullable=True))
    _add_index("ix_material_platform_assets_status", "material_platform_assets", ["user_id", "platform", "normalized_status"])
    op.execute(
        "UPDATE material_platform_assets SET normalized_status = CASE "
        "WHEN lower(coalesce(remote_status, '')) IN ('active', 'ready', 'completed', 'published') THEN 'ready' "
        "WHEN lower(coalesce(remote_status, '')) IN ('processing', 'pending', 'uploading') THEN 'processing' "
        "WHEN lower(coalesce(remote_status, '')) IN ('failed', 'error', 'rejected', 'disapproved') THEN 'failed' "
        "ELSE 'unknown' END"
    )

    _add_column("material_sync_runs", sa.Column("direction", sa.String(length=20), nullable=False, server_default="import"))
    _add_column("material_sync_runs", sa.Column("platform", sa.String(length=32), nullable=False, server_default="Meta"))
    _add_column("material_sync_runs", sa.Column("processing_count", sa.Integer(), nullable=False, server_default="0"))
    _add_index("ix_material_sync_runs_user_direction", "material_sync_runs", ["user_id", "direction", "started_at"])

    _add_column("material_sync_run_items", sa.Column("status", sa.String(length=20), nullable=False, server_default="completed"))
    _add_column("material_sync_run_items", sa.Column("error_code", sa.String(length=50), nullable=True))
    _add_column("material_sync_run_items", sa.Column("started_at", sa.DateTime(), nullable=True))
    _add_column("material_sync_run_items", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE material_sync_run_items SET updated_at = COALESCE(updated_at, processed_at, CURRENT_TIMESTAMP)")


def downgrade() -> None:
    op.drop_column("material_sync_run_items", "updated_at")
    op.drop_column("material_sync_run_items", "started_at")
    op.drop_column("material_sync_run_items", "error_code")
    op.drop_column("material_sync_run_items", "status")
    op.drop_index("ix_material_sync_runs_user_direction", table_name="material_sync_runs")
    op.drop_column("material_sync_runs", "processing_count")
    op.drop_column("material_sync_runs", "platform")
    op.drop_column("material_sync_runs", "direction")
    op.drop_index("ix_material_platform_assets_status", table_name="material_platform_assets")
    op.drop_column("material_platform_assets", "last_error")
    op.drop_column("material_platform_assets", "last_verified_at")
    op.drop_column("material_platform_assets", "normalized_status")
    op.drop_column("material_platform_assets", "created_via")
    op.drop_index("ix_materials_user_processing", table_name="materials")
    op.drop_index("ix_materials_user_lifecycle", table_name="materials")
    op.drop_column("materials", "updated_at")
    op.drop_column("materials", "archived_at")
    op.drop_column("materials", "processing_status")
    op.drop_column("materials", "lifecycle_status")
    op.drop_column("materials", "original_filename")
