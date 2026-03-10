"""add product image url

Revision ID: 1f2e3d4c5b6a
Revises: 9f4fd074c977
Create Date: 2026-03-10 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1f2e3d4c5b6a"
down_revision: Union[str, Sequence[str], None] = "9f4fd074c977"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("image_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "image_url")
