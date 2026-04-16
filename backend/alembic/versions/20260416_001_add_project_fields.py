"""add_project_target_roi_and_region

Revision ID: 20260416_001
Revises: previous_revision
Create Date: 2026-04-16

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260416_001'
down_revision = '9433ed53c61d'  # 上一个迁移版本
branch_labels = None
depends_on = None


def upgrade():
    # 添加 target_roi 字段
    op.add_column('projects', sa.Column('target_roi', sa.Float(), nullable=True))

    # 添加 product_type 字段（与 game_type 合并使用）
    op.add_column('projects', sa.Column('product_type', sa.String(50), nullable=True))

    # 添加 region 字段（JSON 数组）
    op.add_column('projects', sa.Column('region', sa.Text(), nullable=True))

    # 设置默认值
    op.execute("UPDATE projects SET target_roi = 2.0 WHERE target_roi IS NULL")
    op.execute("UPDATE projects SET product_type = game_type WHERE product_type IS NULL")
    op.execute("UPDATE projects SET region = '[]' WHERE region IS NULL")


def downgrade():
    op.drop_column('projects', 'region')
    op.drop_column('projects', 'product_type')
    op.drop_column('projects', 'target_roi')
