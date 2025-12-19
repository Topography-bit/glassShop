from app.dao import BaseDAO
from app.users.models import User


class UserDAO(BaseDAO):
    model = User