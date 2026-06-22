"""add project and campaign meta fields

Revision ID: add_project_campaign_meta_fields
Revises: add_sub_account_bindings
Create Date: 2026-06-21 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_project_campaign_meta_fields'
down_revision = 'dabe7fdbca6d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 为 projects 表添加新字段
    op.add_column('projects', sa.Column('product', sa.String(255), nullable=True, comment='产品名称，例如：休闲消除手游'))
    
    # 为 campaigns 表添加平台绑定字段
    op.add_column('campaigns', sa.Column('account_id', sa.String(100), nullable=True, comment='广告账户ID，对应 sub_account_bindings.sub_account_id'))
    op.add_column('campaigns', sa.Column('platform_campaign_id', sa.String(100), nullable=True, comment='平台广告系列ID，用于与Meta/Google/TikTok平台创建的Campaign ID进行绑定同步'))
    op.add_column('campaigns', sa.Column('countries', sa.String(500), nullable=True, comment='投放国家，例如：美国 / 加拿大'))
    
    # 为 campaigns 表添加 Meta 广告特定字段
    op.add_column('campaigns', sa.Column('objective', sa.String(100), nullable=True, comment='广告目标，例如：App promotion, Conversions, Traffic'))
    op.add_column('campaigns', sa.Column('buying_type', sa.String(50), nullable=True, comment='购买类型，例如：Auction, Reserved'))
    op.add_column('campaigns', sa.Column('special_ad_categories', sa.String(100), nullable=True, comment='特殊广告类别，例如：None, Credit, Employment, Housing'))
    op.add_column('campaigns', sa.Column('ab_test', sa.String(50), nullable=True, comment='A/B测试开关：开启/关闭'))
    op.add_column('campaigns', sa.Column('campaign_budget_optimization', sa.String(50), nullable=True, comment='Campaign预算优化开关：开启/关闭'))
    op.add_column('campaigns', sa.Column('budget_type', sa.String(50), nullable=True, comment='预算类型：Daily budget / Lifetime budget'))
    op.add_column('campaigns', sa.Column('bid_strategy', sa.String(100), nullable=True, comment='出价策略：Lowest cost, Cost cap, Bid cap, ROAS goal'))
    op.add_column('campaigns', sa.Column('spend_limit', sa.Float(), nullable=True, comment='花费限制金额'))
    
    # 为 platform_campaign_id 添加索引以提高查询性能
    op.create_index('ix_campaigns_platform_campaign_id', 'campaigns', ['platform_campaign_id'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('ix_campaigns_platform_campaign_id', 'campaigns')
    
    # 删除 campaigns 表的新字段
    op.drop_column('campaigns', 'spend_limit')
    op.drop_column('campaigns', 'bid_strategy')
    op.drop_column('campaigns', 'budget_type')
    op.drop_column('campaigns', 'campaign_budget_optimization')
    op.drop_column('campaigns', 'ab_test')
    op.drop_column('campaigns', 'special_ad_categories')
    op.drop_column('campaigns', 'buying_type')
    op.drop_column('campaigns', 'objective')
    op.drop_column('campaigns', 'countries')
    op.drop_column('campaigns', 'platform_campaign_id')
    op.drop_column('campaigns', 'account_id')
    
    # 删除 projects 表的新字段
    op.drop_column('projects', 'product')
