from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class SYooKassaCheckoutIn(BaseModel):
    address: str = Field(..., min_length=5, max_length=300)
    normalized_address: str | None = Field(default=None, max_length=300)
    lat: float | None = None
    lon: float | None = None


class SPaymentOrderOut(BaseModel):
    order_id: int = Field(..., ge=1)
    provider: str
    status: str
    payment_status: str
    currency: str
    subtotal_price: Decimal = Field(..., ge=Decimal("0.00"))
    delivery_price: Decimal = Field(..., ge=Decimal("0.00"))
    total_price: Decimal = Field(..., ge=Decimal("0.00"))
    confirmation_url: str | None = None
    paid_at: datetime | None = None
    message: str
