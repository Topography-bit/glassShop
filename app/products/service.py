from decimal import Decimal

from sqlalchemy import select

from app.database import new_session
from app.products.models import EdgeProcessingPrice, FacetPrice, TemperingPrice


def calc_price(*, product_price: Decimal, width_mm: int, length_mm: int, qty: int, 
        edge_price: Decimal, tempering_price: Decimal, facet_price: Decimal) -> Decimal:

    price = ((Decimal(width_mm * length_mm) / Decimal("1000000")) * product_price \
    + edge_price + tempering_price + facet_price) * Decimal(str(qty))

    return price 


async def edges_facets_temperings_product(product):
    async with new_session() as session:

        edges = await session.execute(select(EdgeProcessingPrice).filter_by(thickness_mm=product.thickness_mm, is_active=True))
        edges = edges.scalars().all()

        facets = await session.execute(select(FacetPrice).filter_by(is_active=True))
        facets = facets.scalars().all()

        temperings = await session.execute(select(TemperingPrice).filter_by(thickness_mm=product.thickness_mm, is_active=True))
        temperings = temperings.scalars().all()


        return edges, facets, temperings