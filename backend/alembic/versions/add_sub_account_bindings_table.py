"""add sub_account_bindings table

Revision ID: add_sub_account_bindings
Revises: a1b2c3d4e5f6
Create Date: 2026-05-24 16:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_sub_account_bindings'
down_revision = '9201acb91c82'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 sub_account_bindings 表
    op.create_table(
        'sub_account_bindings',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('parent_connection_id', sa.String(36), nullable=False),
        sa.Column('sub_account_name', sa.String(255), nullable=False),
        sa.Column('customer_id', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['parent_connection_id'], ['platform_connections.id'], ondelete='CASCADE'),
    )
    
    # 创建索引
    op.create_index('ix_sub_account_bindings_parent_connection_id', 'sub_account_bindings', ['parent_connection_id'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('ix_sub_account_bindings_parent_connection_id', table_name='sub_account_bindings')
    
    # 删除表
    op.drop_table('sub_account_bindings')
