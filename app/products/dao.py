from app.dao import BaseDAO
from app.products.models import Product


class ProductsDAO(BaseDAO):
    model = Product

    @classmethod
    
