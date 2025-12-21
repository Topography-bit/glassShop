from decimal import Decimal
from sqlalchemy import Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    price_per_m2: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)