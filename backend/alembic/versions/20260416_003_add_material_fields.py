"""add_material_fatigue_and_media_type

Revision ID: 20260416_003
Revises: 20260416_002
Create Date: 2026-04-16

"""
from alembic import op
import sqlalchemy as sa

revision = '20260416_003'
down_revision = '20260416_002'
branch_labels = None
depends_on = None


def upgrade():
    # 添加 fatigue 字段
    op.add_column('materials', sa.Column('fatigue', sa.Float(), nullable=True, default=0.0))

    # 添加 is_hero 字段
    op.add_column('materials', sa.Column('is_hero', sa.Boolean(), nullable=True, default=False))

    # 添加 media_type 字段
    op.add_column('materials', sa.Column('media_type', sa.String(20), nullable=True))

    # 设置默认值
    op.execute("UPDATE materials SET fatigue = 0.0 WHERE fatigue IS NULL")
    op.execute("UPDATE materials SET is_hero = false WHERE is_hero IS NULL")
    op.execute("UPDATE materials SET media_type = 'video' WHERE media_type IS NULL")

    # 创建索引
    op.create_index('idx_materials_fatigue', 'materials', ['fatigue'])
    op.create_index('idx_materials_media_type', 'materials', ['media_type'])


def downgrade():
    op.drop_index('idx_materials_media_type', 'materials')
    op.drop_index('idx_materials_fatigue', 'materials')
    op.drop_column('materials', 'media_type')
    op.drop_column('materials', 'is_hero')
    op.drop_column('materials', 'fatigue')
