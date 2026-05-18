"""make_access_token_nullable

Revision ID: 9201acb91c82
Revises: a1b2c3d4e5f6
Create Date: 2026-05-18 22:50:04.225246

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9201acb91c82'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 将 access_token 字段改为可空
    with op.batch_alter_table('platform_connections', schema=None) as batch_op:
        batch_op.alter_column('access_token',
                              existing_type=sa.Text(),
                              nullable=True)


def downgrade() -> None:
    # 回滚：将 access_token 字段改回不可空
    with op.batch_alter_table('platform_connections', schema=None) as batch_op:
        batch_op.alter_column('access_token',
                              existing_type=sa.Text(),
                              nullable=False)
