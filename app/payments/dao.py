from app.dao import BaseDAO
from app.payments.models import Order


class OrdersDAO(BaseDAO):
    model = Order
