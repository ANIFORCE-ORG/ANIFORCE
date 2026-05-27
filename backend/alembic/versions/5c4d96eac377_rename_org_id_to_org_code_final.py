"""rename_org_id_to_org_code_final

Revision ID: 5c4d96eac377
Revises: c0787e1a59a1
Create Date: 2026-05-27 17:27:39.677010

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c4d96eac377'
down_revision: Union[str, None] = 'c0787e1a59a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite 需要使用 batch_alter_table 来重命名列
    with op.batch_alter_table('organizations') as batch_op:
        # 重命名 org_id 为 org_code
        batch_op.alter_column('org_id', new_column_name='org_code')
        
        # 确保 invite_code 不为空（如果为空则生成）
        # 注意：这一步可能已经在之前的迁移中完成
    
    # 为 invite_code 为 NULL 的记录生成邀请码
    op.execute("UPDATE organizations SET invite_code = 'invite_' || org_code WHERE invite_code IS NULL")
    
    # 设置 invite_code 为 NOT NULL 并添加约束（如果还没有）
    with op.batch_alter_table('organizations') as batch_op:
        batch_op.alter_column('invite_code', nullable=False)
        # 尝试创建唯一约束（如果不存在）
        try:
            batch_op.create_unique_constraint('uq_organizations_invite_code', ['invite_code'])
        except:
            pass  # 约束可能已存在
        # 尝试创建索引（如果不存在）
        try:
            batch_op.create_index('ix_organizations_invite_code', ['invite_code'])
        except:
            pass  # 索引可能已存在


def downgrade() -> None:
    with op.batch_alter_table('organizations') as batch_op:
        # 重命名回 org_id
        batch_op.alter_column('org_code', new_column_name='org_id')
