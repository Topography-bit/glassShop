from pydantic import BaseModel


class SEdgeOut(BaseModel):
    id: int
    edge_shape: str
    edge_type: str
    thickness_mm: int
    price: int
    is_active: bool