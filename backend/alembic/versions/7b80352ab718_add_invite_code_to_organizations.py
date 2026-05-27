"""add_invite_code_to_organizations

Revision ID: 7b80352ab718
Revises: a95094250577
Create Date: 2026-05-27 17:21:36.186220

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b80352ab718'
down_revision: Union[str, None] = 'a95094250577'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite 不支持 ALTER COLUMN，需要使用批量操作
    with op.batch_alter_table('organizations') as batch_op:
        # 添加 invite_code 字段（先设为可空）
        batch_op.add_column(sa.Column('invite_code', sa.String(100), nullable=True))
    
    # 为现有记录生成邀请码
    op.execute("UPDATE organizations SET invite_code = 'invite_' || org_id WHERE invite_code IS NULL")
    
    # 重新创建表以添加 NOT NULL 约束
    with op.batch_alter_table('organizations') as batch_op:
        batch_op.alter_column('invite_code', nullable=False)
        batch_op.create_unique_constraint('uq_organizations_invite_code', ['invite_code'])
        batch_op.create_index('ix_organizations_invite_code', ['invite_code'])


def downgrade() -> None:
    op.drop_index('ix_organizations_invite_code', 'organizations')
    op.drop_constraint('uq_organizations_invite_code', 'organizations', type_='unique')
    op.drop_column('organizations', 'invite_code')
