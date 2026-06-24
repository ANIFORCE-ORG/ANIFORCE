"""add material metadata fields

Revision ID: 260624_01_material_metadata
Revises: 9b1c2d3e4f50
Create Date: 2026-06-24 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "260624_01_material_metadata"
down_revision: Union[str, None] = "9b1c2d3e4f50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    rows = conn.exec_driver_sql(f"PRAGMA table_info('{table}')").fetchall()
    return any(row[1] == column for row in rows)


def _add_column_if_not_exists(table: str, column: sa.Column) -> None:
    if not _column_exists(table, column.name):
        op.add_column(table, column)


def upgrade() -> None:
    columns = [
        sa.Column("poster_url", sa.Text(), nullable=True),
        sa.Column("preview_url", sa.Text(), nullable=True),
        sa.Column("media_kind", sa.String(length=20), nullable=True),
        sa.Column("format", sa.String(length=20), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("ratio", sa.String(length=20), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("creator", sa.String(length=100), nullable=True),
        sa.Column("rights", sa.String(length=100), nullable=True),
        sa.Column("platforms", sa.Text(), nullable=True),
        sa.Column("review_status", sa.String(length=50), nullable=True),
        sa.Column("source_account", sa.String(length=100), nullable=True),
        sa.Column("placements", sa.Text(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("fatigue", sa.Integer(), nullable=True),
    ]
    for col in columns:
        _add_column_if_not_exists("materials", col)


def downgrade() -> None:
    columns_to_drop = [
        "fatigue", "score", "placements", "source_account", "review_status",
        "platforms", "rights", "creator", "source", "ratio", "height", "width",
        "format", "media_kind", "preview_url", "poster_url",
    ]
    for col in columns_to_drop:
        if _column_exists("materials", col):
            op.drop_column("materials", col)
