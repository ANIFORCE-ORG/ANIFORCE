"""allow platform assets to outlive local materials

Revision ID: 260728_05_detach_platform_assets
Revises: 260728_04_material_asset_identity
Create Date: 2026-07-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "260728_05_detach_platform_assets"
down_revision: Union[str, None] = "260728_04_material_asset_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NAMING_CONVENTION = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
}


def upgrade() -> None:
    with op.batch_alter_table(
        "material_platform_assets", naming_convention=NAMING_CONVENTION
    ) as batch_op:
        batch_op.alter_column(
            "material_id",
            existing_type=sa.String(length=36),
            nullable=True,
            existing_nullable=False,
        )
        batch_op.drop_constraint(
            "fk_material_platform_assets_material_id_materials",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_material_platform_assets_material_id_materials",
            "materials",
            ["material_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    orphan_count = op.get_bind().execute(
        sa.text("SELECT COUNT(*) FROM material_platform_assets WHERE material_id IS NULL")
    ).scalar_one()
    if orphan_count:
        raise RuntimeError("Cannot downgrade while detached platform assets exist")
    with op.batch_alter_table(
        "material_platform_assets", naming_convention=NAMING_CONVENTION
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_material_platform_assets_material_id_materials",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_material_platform_assets_material_id_materials",
            "materials",
            ["material_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.alter_column(
            "material_id",
            existing_type=sa.String(length=36),
            nullable=False,
            existing_nullable=True,
        )
