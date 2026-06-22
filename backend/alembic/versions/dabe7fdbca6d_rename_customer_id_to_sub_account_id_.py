"""rename_customer_id_to_sub_account_id_and_add_bm_customer_id

Revision ID: dabe7fdbca6d
Revises: df88c904758f
Create Date: 2026-06-16 21:09:47.253572

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dabe7fdbca6d'
down_revision: Union[str, None] = 'df88c904758f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new bm_customer_id column
    op.add_column('sub_account_bindings', sa.Column('bm_customer_id', sa.String(length=100), nullable=True))
    
    # Rename customer_id to sub_account_id
    op.alter_column('sub_account_bindings', 'customer_id', new_column_name='sub_account_id')


def downgrade() -> None:
    # Rename sub_account_id back to customer_id
    op.alter_column('sub_account_bindings', 'sub_account_id', new_column_name='customer_id')
    
    # Drop bm_customer_id column
    op.drop_column('sub_account_bindings', 'bm_customer_id')
