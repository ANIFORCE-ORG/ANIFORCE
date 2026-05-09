"""add_material_legacy_performance_fields

Revision ID: 20260509_001
Revises: 20260416_003
Create Date: 2026-05-09

"""
from alembic import op
import sqlalchemy as sa


revision = "20260509_001"
down_revision = "20260416_003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("materials", sa.Column("roi", sa.Float(), nullable=True))
    op.add_column("materials", sa.Column("spend", sa.Float(), nullable=True))
    op.add_column("materials", sa.Column("campaign_id", sa.String(36), nullable=True))
    op.create_index("idx_materials_campaign_id", "materials", ["campaign_id"])


def downgrade():
    op.drop_index("idx_materials_campaign_id", table_name="materials")
    op.drop_column("materials", "campaign_id")
    op.drop_column("materials", "spend")
    op.drop_column("materials", "roi")
