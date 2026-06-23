"""add_meta_campaign_fields_v2

Revision ID: 4951fcc09d73
Revises: add_project_campaign_meta_fields
Create Date: 2026-06-24 00:14:08.852312

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4951fcc09d73'
down_revision: Union[str, None] = 'add_project_campaign_meta_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 Meta Campaign 新字段
    op.add_column('campaigns', sa.Column('special_ad_category_country', sa.String(500), nullable=True, comment='特殊广告类别国家列表，JSON数组格式，例如：["US", "CA"]'))
    op.add_column('campaigns', sa.Column('promoted_object', sa.Text(), nullable=True, comment='推广对象配置，JSON格式，包含 application_id, pixel_id, page_id 等'))
    op.add_column('campaigns', sa.Column('budget_schedule_specs', sa.Text(), nullable=True, comment='预算排期规格，JSON数组格式'))
    op.add_column('campaigns', sa.Column('pacing_type', sa.String(50), nullable=True, comment='投放节奏类型：standard, day_parting'))


def downgrade() -> None:
    # 删除添加的字段
    op.drop_column('campaigns', 'pacing_type')
    op.drop_column('campaigns', 'budget_schedule_specs')
    op.drop_column('campaigns', 'promoted_object')
    op.drop_column('campaigns', 'special_ad_category_country')
