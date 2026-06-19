"""add_system_role_to_users

Revision ID: df88c904758f
Revises: bc612867f29f
Create Date: 2026-06-12 23:34:25.251483

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df88c904758f'
down_revision: Union[str, None] = 'bc612867f29f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('system_role', sa.Enum('ADMIN', 'USER', name='systemrole'), nullable=False, server_default='USER'))


def downgrade() -> None:
    op.drop_column('users', 'system_role')
    op.execute('DROP TYPE IF EXISTS systemrole')
