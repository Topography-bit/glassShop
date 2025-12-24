from app.dao import BaseDAO
from app.products.models import Product, Product_Category


class ProductsDAO(BaseDAO):
    model = Product


class CategoriesDAO(BaseDAO):
    model = Product_Category