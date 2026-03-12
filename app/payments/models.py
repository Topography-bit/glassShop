from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.users.models import User


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    subtotal_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    delivery_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    delivery_distance_km: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    delivery_address: Mapped[str] = mapped_column(String(300), nullable=False)
    delivery_normalized_address: Mapped[str | None] = mapped_column(String(300), nullable=True)

    yookassa_payment_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    confirmation_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    items_payload: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    provider_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    user: Mapped["User"] = relationship()
