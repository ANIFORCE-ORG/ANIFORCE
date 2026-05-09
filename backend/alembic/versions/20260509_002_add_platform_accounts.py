"""add_platform_accounts

Revision ID: 20260509_002
Revises: 20260509_001
Create Date: 2026-05-09

"""
from alembic import op
import sqlalchemy as sa


revision = "20260509_002"
down_revision = "20260509_001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "platform_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("account_id", sa.String(128), nullable=False),
        sa.Column("account_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("currency", sa.String(16), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=True),
        sa.Column("business_manager_id", sa.String(128), nullable=True),
        sa.Column("account_type", sa.String(64), nullable=True),
        sa.Column("account_property", sa.String(64), nullable=True),
        sa.Column("source_type", sa.String(64), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("balance", sa.Float(), nullable=True),
        sa.Column("amount_spent", sa.Float(), nullable=True),
        sa.Column("available_balance", sa.Float(), nullable=True),
        sa.Column("frozen_balance", sa.Float(), nullable=True),
        sa.Column("survival_days", sa.Integer(), nullable=True),
        sa.Column("usage_days", sa.Integer(), nullable=True),
        sa.Column("meta_account_status", sa.Integer(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("connected_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_platform_accounts_user_id", "platform_accounts", ["user_id"])
    op.create_index("idx_platform_accounts_platform", "platform_accounts", ["platform"])
    op.create_index("idx_platform_accounts_account_id", "platform_accounts", ["account_id"])
    op.create_index("idx_platform_accounts_status", "platform_accounts", ["status"])
    op.create_index("idx_platform_accounts_business_manager_id", "platform_accounts", ["business_manager_id"])

    op.create_table(
        "platform_account_operations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("account_pk", sa.String(36), sa.ForeignKey("platform_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("operation_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(16), nullable=True),
        sa.Column("target_id", sa.String(128), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_platform_account_operations_account_pk", "platform_account_operations", ["account_pk"])
    op.create_index("idx_platform_account_operations_operation_type", "platform_account_operations", ["operation_type"])
    op.create_index("idx_platform_account_operations_status", "platform_account_operations", ["status"])

    op.create_table(
        "platform_connections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=True),
        sa.Column("app_id", sa.String(255), nullable=True),
        sa.Column("app_secret", sa.Text(), nullable=True),
        sa.Column("redirect_uri", sa.Text(), nullable=True),
        sa.Column("scopes", sa.Text(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_connected_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_platform_connections_user_id", "platform_connections", ["user_id"])
    op.create_index("idx_platform_connections_platform", "platform_connections", ["platform"])
    op.create_index("idx_platform_connections_status", "platform_connections", ["status"])


def downgrade():
    op.drop_index("idx_platform_connections_status", table_name="platform_connections")
    op.drop_index("idx_platform_connections_platform", table_name="platform_connections")
    op.drop_index("idx_platform_connections_user_id", table_name="platform_connections")
    op.drop_table("platform_connections")

    op.drop_index("idx_platform_account_operations_status", table_name="platform_account_operations")
    op.drop_index("idx_platform_account_operations_operation_type", table_name="platform_account_operations")
    op.drop_index("idx_platform_account_operations_account_pk", table_name="platform_account_operations")
    op.drop_table("platform_account_operations")

    op.drop_index("idx_platform_accounts_business_manager_id", table_name="platform_accounts")
    op.drop_index("idx_platform_accounts_status", table_name="platform_accounts")
    op.drop_index("idx_platform_accounts_account_id", table_name="platform_accounts")
    op.drop_index("idx_platform_accounts_platform", table_name="platform_accounts")
    op.drop_index("idx_platform_accounts_user_id", table_name="platform_accounts")
    op.drop_table("platform_accounts")
