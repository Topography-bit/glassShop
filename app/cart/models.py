from decimal import Decimal
from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.products.models import EdgeProcessingPrice, FacetPrice, Product, TemperingPrice
from app.users.models import User


class Cart(Base):
    __tablename__ = "carts"


    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))

    width_mm: Mapped[int] = mapped_column()
    length_mm: Mapped[int]= mapped_column()
    quantity: Mapped[int]= mapped_column(default=1)

    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))


    edge_id: Mapped[int | None] = mapped_column(ForeignKey("glass_edge_processing_prices.id"), nullable=True)
    facet_id: Mapped[int | None] = mapped_column(ForeignKey("facet_prices.id"), nullable=True)
    tempering_id: Mapped[int | None] = mapped_column(ForeignKey("tempering_prices.id"), nullable=True)

    user: Mapped["User"] = relationship()
    product: Mapped["Product"] = relationship()
    edge: Mapped["EdgeProcessingPrice"] = relationship()
    facet: Mapped["FacetPrice"] = relationship()
    tempering: Mapped["TemperingPrice"] = relationship()