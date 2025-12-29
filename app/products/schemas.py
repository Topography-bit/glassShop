from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Optional
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

    model_config = ConfigDict(from_attributes=True)


class EdgeSchema(BaseModel):
    id: int
    edge_shape: Literal["straight", "curved"]
    edge_type: Literal["matte", "transparent"]
    price: Decimal

    model_config = ConfigDict(from_attributes=True)


class SEdgeUpdate(BaseModel):
    edge_shape: Literal["straight", "curved"]
    edge_type: Literal["matte", "transparent"]
    thickness_mm: int = Field(..., ge=1)
    price: Decimal = Field(ge=0)
    is_active: bool


class SEdgeOut(BaseModel):
    id: int
    edge_shape: Literal["straight", "curved"]
    edge_type: Literal["matte", "transparent"]
    thickness_mm: int = Field(..., ge=1)
    price: Decimal
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class FacetSchema(BaseModel):
    id: int
    shape: Literal["straight", "curved"]
    facet_width_mm: int = Field(..., ge=1)
    price: Decimal

    model_config = ConfigDict(from_attributes=True)


class SFacetUpdate(BaseModel):
    shape: Literal["straight", "curved"]
    facet_width_mm: int = Field(..., ge=1)
    price: Decimal
    is_active: bool


class SFacetOut(BaseModel):
    id: int
    shape: Literal["straight", "curved"]
    facet_width_mm: int = Field(..., ge=1)
    price: Decimal
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


class TemperingSchema(BaseModel):
    id: int
    thickness_mm: int = Field(..., ge=1)
    price: Decimal

    model_config = ConfigDict(from_attributes=True)


class STemperingUpdate(BaseModel):
    thickness_mm: int = Field(..., ge=1)
    price: Decimal
    is_active: bool


class STemperingOut(BaseModel):
    id: int
    thickness_mm: int = Field(..., ge=1)
    price: Decimal
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ConfigSchema(BaseModel):
    product: ProductSchema
    edges: list[EdgeSchema]
    facets: list[FacetSchema]
    temperings: list[TemperingSchema]


class PriceResponse(BaseModel):
    price: Decimal
