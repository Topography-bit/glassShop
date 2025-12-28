from decimal import Decimal
from pydantic import BaseModel, ConfigDict

from app.products.schemas import EdgeSchema, FacetSchema, ProductSchema, TemperingSchema


class SCartResponse(BaseModel):
    id: int
    user_id: int
    product_id: int

    width_mm: int
    length_mm: int
    quantity: int
    price: Decimal

    edge_id: int | None = None
    facet_id: int | None = None
    tempering_id: int | None = None

    model_config = ConfigDict(from_attributes=True)