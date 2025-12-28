from app.cart.models import Cart
from app.dao import BaseDAO


class CartsDAO(BaseDAO):
    model = Cart