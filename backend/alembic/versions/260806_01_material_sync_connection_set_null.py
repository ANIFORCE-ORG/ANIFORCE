"""preserve material transfer records when a connection is removed

Revision ID: 260806_01_material_sync_connection_set_null
Revises: 260728_05_detach_platform_assets
Create Date: 2026-08-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "260806_01_material_sync_connection_set_null"
down_revision: Union[str, None] = "260728_05_detach_platform_assets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NAMING_CONVENTION = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
}


def upgrade() -> None:
    for table in ("material_platform_assets", "material_sync_runs"):
        with op.batch_alter_table(table, naming_convention=NAMING_CONVENTION) as batch_op:
            batch_op.drop_constraint(
                f"fk_{table}_connection_id_platform_connections",
                type_="foreignkey",
            )
            batch_op.create_foreign_key(
                f"fk_{table}_connection_id_platform_connections",
                "platform_connections",
                ["connection_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    for table in ("material_platform_assets", "material_sync_runs"):
        with op.batch_alter_table(table, naming_convention=NAMING_CONVENTION) as batch_op:
            batch_op.drop_constraint(
                f"fk_{table}_connection_id_platform_connections",
                type_="foreignkey",
            )
            batch_op.create_foreign_key(
                f"fk_{table}_connection_id_platform_connections",
                "platform_connections",
                ["connection_id"],
                ["id"],
                ondelete="CASCADE",
            )
