from decimal import Decimal
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field

width_len = Annotated[int | None, Field(default=None, ge=100)]


class SCartAdd(BaseModel):
    product_id: int = Field(..., ge=1)

    width_mm: width_len
    length_mm: width_len

    qty: int = Field(..., ge=1, lt=100)

    edge_id: int | None = None
    facet_id: int | None = None
    tempering_id: int | None = None


class SCartItemResponse(BaseModel):
    id: int = Field(..., ge=1)

    user_id: int = Field(..., ge=1)
    product_id: int = Field(..., ge=1)

    width_mm: width_len
    length_mm: width_len
    quantity: int = Field(..., ge=1, lt=100)
    price: Decimal = Field(..., ge=Decimal("0.00"))

    edge_id: int | None = None
    facet_id: int | None = None
    tempering_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class SCartChangeQty(BaseModel):
    cart_prod_id: int = Field(..., ge=1)
    qty: int = Field(..., ge=1, lt=100)


class SCartDeliveryQuoteIn(BaseModel):
    address: str = Field(..., min_length=5, max_length=300)
    normalized_address: str | None = Field(default=None, max_length=300)
    lat: float | None = None
    lon: float | None = None


class SCartDeliveryQuoteOut(BaseModel):
    address: str
    normalized_address: str | None = None
    distance_km: Decimal = Field(..., ge=Decimal("0.00"))
    delivery_price: Decimal = Field(..., ge=Decimal("0.00"))
    subtotal_price: Decimal = Field(..., ge=Decimal("0.00"))
    total_price: Decimal = Field(..., ge=Decimal("0.00"))
    within_radius: bool
    can_order: bool
    message: str | None = None


class SCartDeliverySuggestionOut(BaseModel):
    title: str
    subtitle: str | None = None
    full_address: str
    distance_km: Decimal = Field(..., ge=Decimal("0.00"))
    within_radius: bool
    lat: float
    lon: float
