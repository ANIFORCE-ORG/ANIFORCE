"""Add platform_connections table

Revision ID: a1b2c3d4e5f6
Revises: 9433ed53c61d
Create Date: 2026-05-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '9433ed53c61d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 platform_connections 表
    op.create_table(
        'platform_connections',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('account_id', sa.String(length=255), nullable=False),
        sa.Column('account_name', sa.String(length=255), nullable=True),
        sa.Column('account_secret', sa.String(length=255), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_type', sa.String(length=50), nullable=False),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('scopes', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('extra_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'platform', 'account_id', name='uq_user_platform_account')
    )
    
    # 创建索引
    op.create_index(op.f('ix_platform_connections_user_id'), 'platform_connections', ['user_id'], unique=False)
    op.create_index(op.f('ix_platform_connections_platform'), 'platform_connections', ['platform'], unique=False)


def downgrade() -> None:
    # 删除索引
    op.drop_index(op.f('ix_platform_connections_platform'), table_name='platform_connections')
    op.drop_index(op.f('ix_platform_connections_user_id'), table_name='platform_connections')
    
    # 删除表
    op.drop_table('platform_connections')
