"""add orders table for yookassa

Revision ID: 3b1d4f2a8c91
Revises: 1f2e3d4c5b6a
Create Date: 2026-03-11 22:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3b1d4f2a8c91"
down_revision: Union[str, Sequence[str], None] = "1f2e3d4c5b6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payment_status", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("subtotal_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("delivery_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("total_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("delivery_distance_km", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("delivery_address", sa.String(length=300), nullable=False),
        sa.Column("delivery_normalized_address", sa.String(length=300), nullable=True),
        sa.Column("yookassa_payment_id", sa.String(length=128), nullable=True),
        sa.Column("confirmation_url", sa.String(length=2048), nullable=True),
        sa.Column("items_payload", sa.JSON(), nullable=False),
        sa.Column("provider_payload", sa.JSON(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("yookassa_payment_id"),
    )
    op.create_index(op.f("ix_orders_user_id"), "orders", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_orders_user_id"), table_name="orders")
    op.drop_table("orders")
