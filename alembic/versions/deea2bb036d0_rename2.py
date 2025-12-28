"""rename2

Revision ID: deea2bb036d0
Revises: fd8cc4507b56
Create Date: 2025-12-27 00:32:16.834158

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'deea2bb036d0'
down_revision: Union[str, Sequence[str], None] = 'fd8cc4507b56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column(
        "products",
        "min_width_mm",
        new_column_name="min_width"
    )
    op.alter_column(
        "products",
        "min_height_mm",
        new_column_name="min_length"
    )


def downgrade():
    op.alter_column(
        "products",
        "min_width_mm",
        new_column_name="min_width"
    )
    op.alter_column(
        "products",
        "min_height_mm",
        new_column_name="min_length"
    )