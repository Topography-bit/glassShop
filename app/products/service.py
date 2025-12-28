from decimal import Decimal


def calc_price(*, product_price: Decimal, width_mm: int, length_mm: int, qty: int, 
        edge_price: Decimal, tempering_price: Decimal, facet_price: Decimal) -> Decimal:

    price = ((Decimal(width_mm * length_mm) / Decimal("1000000")) * product_price \
    + edge_price + tempering_price + facet_price) * Decimal(str(qty))

    return price 