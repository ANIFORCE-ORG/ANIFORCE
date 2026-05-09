"""agent_account_campaign_linkage

Revision ID: 20260509_003
Revises: 20260509_002
Create Date: 2026-05-09

"""
from alembic import op
import sqlalchemy as sa


revision = "20260509_003"
down_revision = "20260509_002"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("campaigns") as batch_op:
        batch_op.add_column(sa.Column("platform_account_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("external_campaign_id", sa.String(128), nullable=True))
        batch_op.add_column(sa.Column("external_status", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("objective", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("budget_type", sa.String(32), nullable=True))
        batch_op.add_column(sa.Column("daily_budget", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("lifetime_budget", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("bid_strategy", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("last_synced_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("last_sync_error", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            "fk_campaigns_platform_account_id_platform_accounts",
            "platform_accounts",
            ["platform_account_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index("idx_campaigns_platform_account_id", "campaigns", ["platform_account_id"])
    op.create_index("idx_campaigns_external_campaign_id", "campaigns", ["external_campaign_id"])
    op.create_index("idx_campaigns_external_status", "campaigns", ["external_status"])

    op.create_table(
        "project_platform_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform_account_id", sa.String(36), sa.ForeignKey("platform_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(32), nullable=True),
        sa.Column("status", sa.String(32), nullable=True),
        sa.Column("spend_cap", sa.Float(), nullable=True),
        sa.Column("daily_cap", sa.Float(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("project_id", "platform_account_id", name="uq_project_platform_account"),
    )
    op.create_index("idx_project_platform_accounts_project_id", "project_platform_accounts", ["project_id"])
    op.create_index("idx_project_platform_accounts_platform_account_id", "project_platform_accounts", ["platform_account_id"])
    op.create_index("idx_project_platform_accounts_role", "project_platform_accounts", ["role"])
    op.create_index("idx_project_platform_accounts_status", "project_platform_accounts", ["status"])

    op.create_table(
        "agent_actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform_account_id", sa.String(36), sa.ForeignKey("platform_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("risk_level", sa.String(8), nullable=True),
        sa.Column("status", sa.String(32), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("evidence_json", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("expected_impact_json", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(32), nullable=True),
        sa.Column("confirmed_by", sa.String(36), nullable=True),
        sa.Column("executed_by", sa.String(36), nullable=True),
        sa.Column("execution_result_json", sa.Text(), nullable=True),
        sa.Column("outcome_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_agent_actions_user_id", "agent_actions", ["user_id"])
    op.create_index("idx_agent_actions_project_id", "agent_actions", ["project_id"])
    op.create_index("idx_agent_actions_platform_account_id", "agent_actions", ["platform_account_id"])
    op.create_index("idx_agent_actions_campaign_id", "agent_actions", ["campaign_id"])
    op.create_index("idx_agent_actions_action_type", "agent_actions", ["action_type"])
    op.create_index("idx_agent_actions_risk_level", "agent_actions", ["risk_level"])
    op.create_index("idx_agent_actions_status", "agent_actions", ["status"])


def downgrade():
    op.drop_index("idx_agent_actions_status", table_name="agent_actions")
    op.drop_index("idx_agent_actions_risk_level", table_name="agent_actions")
    op.drop_index("idx_agent_actions_action_type", table_name="agent_actions")
    op.drop_index("idx_agent_actions_campaign_id", table_name="agent_actions")
    op.drop_index("idx_agent_actions_platform_account_id", table_name="agent_actions")
    op.drop_index("idx_agent_actions_project_id", table_name="agent_actions")
    op.drop_index("idx_agent_actions_user_id", table_name="agent_actions")
    op.drop_table("agent_actions")

    op.drop_index("idx_project_platform_accounts_status", table_name="project_platform_accounts")
    op.drop_index("idx_project_platform_accounts_role", table_name="project_platform_accounts")
    op.drop_index("idx_project_platform_accounts_platform_account_id", table_name="project_platform_accounts")
    op.drop_index("idx_project_platform_accounts_project_id", table_name="project_platform_accounts")
    op.drop_table("project_platform_accounts")

    op.drop_index("idx_campaigns_external_status", table_name="campaigns")
    op.drop_index("idx_campaigns_external_campaign_id", table_name="campaigns")
    op.drop_index("idx_campaigns_platform_account_id", table_name="campaigns")
    with op.batch_alter_table("campaigns") as batch_op:
        batch_op.drop_constraint("fk_campaigns_platform_account_id_platform_accounts", type_="foreignkey")
        batch_op.drop_column("last_sync_error")
        batch_op.drop_column("last_synced_at")
        batch_op.drop_column("bid_strategy")
        batch_op.drop_column("lifetime_budget")
        batch_op.drop_column("daily_budget")
        batch_op.drop_column("budget_type")
        batch_op.drop_column("objective")
        batch_op.drop_column("external_status")
        batch_op.drop_column("external_campaign_id")
        batch_op.drop_column("platform_account_id")
