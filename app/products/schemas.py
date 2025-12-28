from pydantic import BaseModel, ConfigDict
from typing import Optional
from decimal import Decimal

class ProductSchema(BaseModel):
    id: int
    name: str
    price_per_m2: Decimal
    thickness_mm: int | None
    min_width: int | None
    min_length: int | None
    max_width: int | None
    max_length: int | None


class EdgeSchema(BaseModel):
    id: int
    edge_shape: str
    edge_type: str
    price: int


class FacetSchema(BaseModel):
    id: int
    shape: str
    facet_width_mm: int
    price: int


class TemperingSchema(BaseModel):
    id: int
    thickness_mm: int
    price: int


class ConfigSchema(BaseModel):
    product: ProductSchema
    edges: list[EdgeSchema]
    facets: list[FacetSchema]
    temperings: list[TemperingSchema]

class PriceResponse(BaseModel):
    price: Decimal