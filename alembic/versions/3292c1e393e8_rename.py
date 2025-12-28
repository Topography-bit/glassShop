"""rename

Revision ID: 3292c1e393e8
Revises: 065e3186b8b3
Create Date: 2025-12-26 23:57:30.678947

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3292c1e393e8'
down_revision: Union[str, Sequence[str], None] = '065e3186b8b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column(
        "facet_prices",
        "price_rub",
        new_column_name="price"
    )
    op.alter_column(
        "glass_edge_processing_prices",
        "price_rub",
        new_column_name="price"
    )
    op.alter_column(
        "tempering_prices",
        "price_rub",
        new_column_name="price"
    )

def downgrade():
    op.alter_column(
        "facet_prices",
        "price",
        new_column_name="price_rub"
    )
    op.alter_column(
        "glass_edge_processing_prices",
        "price",
        new_column_name="price_rub"
    )
    op.alter_column(
        "tempering_prices",
        "price",
        new_column_name="price_rub"
    )
