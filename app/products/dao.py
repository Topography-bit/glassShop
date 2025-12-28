from app.dao import BaseDAO
from app.products.models import EdgeProcessingPrice, FacetPrice, Product, Product_Category, TemperingPrice


class ProductsDAO(BaseDAO):
    model = Product


class CategoriesDAO(BaseDAO):
    model = Product_Category


class EdgesDAO(BaseDAO):
    model = EdgeProcessingPrice


class TemperingDAO(BaseDAO):
    model = TemperingPrice


class FacetsDAO(BaseDAO):
    model = FacetPrice
