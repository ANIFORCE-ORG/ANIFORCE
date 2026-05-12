"""add_campaign_materials_and_ai_usage

Revision ID: 20260512_001
Revises: 20260509_003
Create Date: 2026-05-12

"""
from alembic import op
import sqlalchemy as sa


revision = "20260512_001"
down_revision = "20260509_003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "campaign_materials",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_id", sa.String(36), sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("copy", sa.Text(), nullable=True),
        sa.Column("source", sa.String(32), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(32), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("campaign_id", "material_id", name="uq_campaign_material"),
    )
    op.create_index("idx_campaign_materials_campaign_id", "campaign_materials", ["campaign_id"])
    op.create_index("idx_campaign_materials_material_id", "campaign_materials", ["material_id"])
    op.create_index("idx_campaign_materials_status", "campaign_materials", ["status"])
    op.create_index("idx_campaign_materials_created_by", "campaign_materials", ["created_by"])

    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scenario", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(32), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column("request_hash", sa.String(128), nullable=True),
        sa.Column("prompt_version", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_ai_usage_logs_user_id", "ai_usage_logs", ["user_id"])
    op.create_index("idx_ai_usage_logs_project_id", "ai_usage_logs", ["project_id"])
    op.create_index("idx_ai_usage_logs_campaign_id", "ai_usage_logs", ["campaign_id"])
    op.create_index("idx_ai_usage_logs_scenario", "ai_usage_logs", ["scenario"])
    op.create_index("idx_ai_usage_logs_status", "ai_usage_logs", ["status"])

    op.create_table(
        "ai_outputs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("usage_log_id", sa.String(36), sa.ForeignKey("ai_usage_logs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scenario", sa.String(64), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True),
        sa.Column("material_id", sa.String(36), sa.ForeignKey("materials.id", ondelete="SET NULL"), nullable=True),
        sa.Column("output_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_ai_outputs_usage_log_id", "ai_outputs", ["usage_log_id"])
    op.create_index("idx_ai_outputs_scenario", "ai_outputs", ["scenario"])
    op.create_index("idx_ai_outputs_status", "ai_outputs", ["status"])

    op.create_table(
        "ai_budgets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("scope_type", sa.String(32), nullable=False),
        sa.Column("scope_id", sa.String(64), nullable=False),
        sa.Column("daily_token_limit", sa.Integer(), nullable=True),
        sa.Column("monthly_token_limit", sa.Integer(), nullable=True),
        sa.Column("daily_cost_limit_usd", sa.Float(), nullable=True),
        sa.Column("monthly_cost_limit_usd", sa.Float(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("scope_type", "scope_id", name="uq_ai_budget_scope"),
    )


def downgrade():
    op.drop_table("ai_budgets")
    op.drop_index("idx_ai_outputs_status", table_name="ai_outputs")
    op.drop_index("idx_ai_outputs_scenario", table_name="ai_outputs")
    op.drop_index("idx_ai_outputs_usage_log_id", table_name="ai_outputs")
    op.drop_table("ai_outputs")
    op.drop_index("idx_ai_usage_logs_status", table_name="ai_usage_logs")
    op.drop_index("idx_ai_usage_logs_scenario", table_name="ai_usage_logs")
    op.drop_index("idx_ai_usage_logs_campaign_id", table_name="ai_usage_logs")
    op.drop_index("idx_ai_usage_logs_project_id", table_name="ai_usage_logs")
    op.drop_index("idx_ai_usage_logs_user_id", table_name="ai_usage_logs")
    op.drop_table("ai_usage_logs")
    op.drop_index("idx_campaign_materials_created_by", table_name="campaign_materials")
    op.drop_index("idx_campaign_materials_status", table_name="campaign_materials")
    op.drop_index("idx_campaign_materials_material_id", table_name="campaign_materials")
    op.drop_index("idx_campaign_materials_campaign_id", table_name="campaign_materials")
    op.drop_table("campaign_materials")
