"""add connection_id to campaigns

Revision ID: 260706_01_add_connection_id
Revises: add_sub_account_bindings
Create Date: 2026-07-06 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '260706_01_add_connection_id'
down_revision = '260629_01_idempotency_records'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 使用 batch 模式来支持 SQLite
    with op.batch_alter_table('campaigns', schema=None) as batch_op:
        # 添加 connection_id 字段
        batch_op.add_column(
            sa.Column('connection_id', sa.String(36), nullable=True)
        )
        
        # 创建外键约束
        batch_op.create_foreign_key(
            'fk_campaigns_connection_id',
            'platform_connections',
            ['connection_id'],
            ['id'],
            ondelete='SET NULL'
        )
        
        # 创建索引
        batch_op.create_index(
            'ix_campaigns_connection_id',
            ['connection_id']
        )


def downgrade() -> None:
    # 使用 batch 模式来支持 SQLite
    with op.batch_alter_table('campaigns', schema=None) as batch_op:
        # 删除索引
        batch_op.drop_index('ix_campaigns_connection_id')
        
        # 删除外键约束
        batch_op.drop_constraint('fk_campaigns_connection_id', type_='foreignkey')
        
        # 删除字段
        batch_op.drop_column('connection_id')
