from pydantic import BaseModel, ConfigDict, Field
from typing import Annotated, Literal
from decimal import Decimal

Id = Annotated[int, Field(..., ge=1)]
min_width_len = Annotated[int | None, Field(default=None, ge=100)]
max_width_len = Annotated[int | None, Field(default=None, ge=100)]
thickness = Annotated[int | None, Field(default=None, ge=1)]
price_type = Annotated[Decimal, Field(ge=Decimal("0.00"))]
shape = Literal["straight", "curved"]
edge_type = Literal["matte", "transparent"]


class ProductSchema(BaseModel):
    id: Id
    name: str = Field(..., min_length=1, max_length=100)
    image_url: str | None = None
    price_per_m2: price_type
    thickness_mm: thickness
    min_width: min_width_len
    min_length: min_width_len
    max_width: max_width_len
    max_length: max_width_len

    model_config = ConfigDict(from_attributes=True)


class SEdgeUpdate(BaseModel):
    edge_shape: shape
    edge_type: edge_type
    thickness_mm: thickness
    price: price_type
    is_active: bool


class SEdgeOut(BaseModel):
    id: Id
    edge_shape: shape
    edge_type: edge_type
    thickness_mm: thickness
    price: price_type
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class SFacetUpdate(BaseModel):
    shape: shape
    facet_width_mm: int = Field(..., ge=1)
    price: price_type
    is_active: bool


class SFacetOut(BaseModel):
    id: Id
    shape: shape
    facet_width_mm: int = Field(..., ge=1)
    price: price_type
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


class STemperingUpdate(BaseModel):
    thickness_mm: thickness
    price: price_type
    is_active: bool


class STemperingOut(BaseModel):
    id: Id
    thickness_mm: thickness
    price: price_type
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ConfigSchema(BaseModel):
    product: ProductSchema
    edges: list[SEdgeOut]
    facets: list[SFacetOut]
    temperings: list[STemperingOut]
