"""rename_org_id_to_org_code_and_add_invite_code

Revision ID: c0787e1a59a1
Revises: 7b80352ab718
Create Date: 2026-05-27 17:24:16.418630

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c0787e1a59a1'
down_revision: Union[str, None] = '7b80352ab718'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite 需要使用 batch_alter_table 来重命名列和添加约束
    with op.batch_alter_table('organizations') as batch_op:
        # 重命名 org_id 为 org_code
        batch_op.alter_column('org_id', new_column_name='org_code')
        
        # 添加 invite_code 字段（如果不存在）
        batch_op.add_column(sa.Column('invite_code', sa.String(100), nullable=True))
    
    # 为现有记录生成邀请码（使用 org_code）
    op.execute("UPDATE organizations SET invite_code = 'invite_' || org_code WHERE invite_code IS NULL")
    
    # 设置 invite_code 为 NOT NULL 并添加约束
    with op.batch_alter_table('organizations') as batch_op:
        batch_op.alter_column('invite_code', nullable=False)
        batch_op.create_unique_constraint('uq_organizations_invite_code', ['invite_code'])
        batch_op.create_index('ix_organizations_invite_code', ['invite_code'])


def downgrade() -> None:
    with op.batch_alter_table('organizations') as batch_op:
        batch_op.drop_index('ix_organizations_invite_code')
        batch_op.drop_constraint('uq_organizations_invite_code', type_='unique')
        batch_op.drop_column('invite_code')
        batch_op.alter_column('org_code', new_column_name='org_id')
