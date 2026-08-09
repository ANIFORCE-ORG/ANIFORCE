"""harden material platform asset identity

Revision ID: 260728_04_material_asset_identity
Revises: 260728_03_material_workspace_states
Create Date: 2026-07-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "260728_04_material_asset_identity"
down_revision: Union[str, None] = "260728_03_material_workspace_states"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Legacy soft-deleted rows are no longer part of the user-visible or audit model.
    op.execute("DELETE FROM material_platform_assets WHERE lower(coalesce(remote_status, '')) = 'missing'")
    op.execute(
        "UPDATE material_platform_assets SET normalized_status = CASE "
        "WHEN lower(coalesce(remote_status, '')) IN ('active', 'ready', 'completed', 'published') THEN 'ready' "
        "WHEN lower(coalesce(remote_status, '')) IN ('processing', 'pending', 'uploading') THEN 'processing' "
        "WHEN lower(coalesce(remote_status, '')) IN ('failed', 'error', 'rejected', 'disapproved') THEN 'failed' "
        "ELSE 'unknown' END"
    )
    op.add_column("material_platform_assets", sa.Column("ad_account_name", sa.String(length=255), nullable=True))
    if sa.inspect(op.get_bind()).has_table("sub_account_bindings"):
        op.execute(
            "UPDATE material_platform_assets SET ad_account_name = ("
            "SELECT sub_account_name FROM sub_account_bindings "
            "WHERE parent_connection_id = material_platform_assets.connection_id "
            "AND replace(sub_account_id, 'act_', '') = replace(material_platform_assets.ad_account_id, 'act_', '') LIMIT 1)"
        )
    with op.batch_alter_table("material_platform_assets") as batch_op:
        batch_op.alter_column("connection_id", existing_type=sa.String(length=36), nullable=True)
    with op.batch_alter_table("material_sync_runs") as batch_op:
        batch_op.alter_column("connection_id", existing_type=sa.String(length=36), nullable=True)
    op.create_index(
        "uq_material_platform_asset_target",
        "material_platform_assets",
        ["material_id", "platform", "ad_account_id", "asset_type"],
        unique=True,
    )
    op.create_index(
        "uq_material_platform_asset_remote_identity",
        "material_platform_assets",
        ["user_id", "platform", "ad_account_id", "asset_type", "external_asset_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_material_platform_asset_remote_identity", table_name="material_platform_assets")
    op.drop_index("uq_material_platform_asset_target", table_name="material_platform_assets")
    with op.batch_alter_table("material_sync_runs") as batch_op:
        batch_op.alter_column("connection_id", existing_type=sa.String(length=36), nullable=False)
    with op.batch_alter_table("material_platform_assets") as batch_op:
        batch_op.alter_column("connection_id", existing_type=sa.String(length=36), nullable=False)
    op.drop_column("material_platform_assets", "ad_account_name")
