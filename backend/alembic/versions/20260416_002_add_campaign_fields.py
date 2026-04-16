"""add_campaign_pipeline_and_metrics

Revision ID: 20260416_002
Revises: 20260416_001
Create Date: 2026-04-16

"""
from alembic import op
import sqlalchemy as sa

revision = '20260416_002'
down_revision = '20260416_001'
branch_labels = None
depends_on = None


def upgrade():
    # 添加 pipeline_step 字段
    op.add_column('campaigns', sa.Column('pipeline_step', sa.String(50), nullable=True))

    # 添加 target_cpa 字段
    op.add_column('campaigns', sa.Column('target_cpa', sa.Float(), nullable=True))

    # 添加 learning_phase 字段
    op.add_column('campaigns', sa.Column('learning_phase', sa.String(50), nullable=True))

    # 添加 auto_optimize_enabled 字段
    op.add_column('campaigns', sa.Column('auto_optimize_enabled', sa.Boolean(), nullable=True, default=False))

    # 添加 optimization_rules 字段（JSON 数组）
    op.add_column('campaigns', sa.Column('optimization_rules', sa.Text(), nullable=True))

    # 设置默认值
    op.execute("UPDATE campaigns SET pipeline_step = 'not_started' WHERE pipeline_step IS NULL AND status = 'draft'")
    op.execute("UPDATE campaigns SET pipeline_step = 'running' WHERE pipeline_step IS NULL AND status = 'running'")
    op.execute("UPDATE campaigns SET pipeline_step = 'paused' WHERE pipeline_step IS NULL AND status = 'paused'")
    op.execute("UPDATE campaigns SET pipeline_step = 'finished' WHERE pipeline_step IS NULL AND status = 'completed'")
    op.execute("UPDATE campaigns SET target_cpa = 3.0 WHERE target_cpa IS NULL")
    op.execute("UPDATE campaigns SET learning_phase = 'active' WHERE learning_phase IS NULL")
    op.execute("UPDATE campaigns SET auto_optimize_enabled = false WHERE auto_optimize_enabled IS NULL")
    op.execute("UPDATE campaigns SET optimization_rules = '[]' WHERE optimization_rules IS NULL")

    # 创建索引
    op.create_index('idx_campaigns_pipeline_step', 'campaigns', ['pipeline_step'])


def downgrade():
    op.drop_index('idx_campaigns_pipeline_step', 'campaigns')
    op.drop_column('campaigns', 'optimization_rules')
    op.drop_column('campaigns', 'auto_optimize_enabled')
    op.drop_column('campaigns', 'learning_phase')
    op.drop_column('campaigns', 'target_cpa')
    op.drop_column('campaigns', 'pipeline_step')
