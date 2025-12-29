from decimal import Decimal
from sqlalchemy import ForeignKey, Numeric, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Product_Category(Base):
    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_name: Mapped[str] = mapped_column(nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    price_per_m2: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    thickness_mm: Mapped[int | None] = mapped_column(nullable=True)
    max_width: Mapped[int] = mapped_column(nullable=True)
    max_length: Mapped[int] = mapped_column(nullable=True)
    min_width: Mapped[int | None] = mapped_column(nullable=True, default=100)
    min_length: Mapped[int | None] = mapped_column(nullable=True, default=100)
    category_id: Mapped[int] = mapped_column(ForeignKey("product_categories.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")

    category: Mapped["Product_Category"] = relationship(back_populates="products")


class EdgeProcessingPrice(Base):
    __tablename__ = "glass_edge_processing_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    edge_shape: Mapped[str] = mapped_column(nullable=False)
    edge_type: Mapped[str] = mapped_column(nullable=False)
    thickness_mm: Mapped[int] = mapped_column(nullable=False)
    price: Mapped[int] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=True, default=True)


class FacetPrice(Base):
    __tablename__ = "facet_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    shape: Mapped[str] = mapped_column(nullable=False)
    facet_width_mm: Mapped[int] = mapped_column(nullable=False)
    price: Mapped[int] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=True, default=True)


class TemperingPrice(Base):
    __tablename__ = "tempering_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    thickness_mm: Mapped[int] = mapped_column(nullable=False)
    price: Mapped[int] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=True, default=True)