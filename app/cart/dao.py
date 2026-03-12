from sqlalchemy import delete

from app.cart.models import Cart
from app.database import new_session
from app.dao import BaseDAO


class CartsDAO(BaseDAO):
    model = Cart

    @classmethod
    async def delete_items(cls, *, user_id: int, item_ids: list[int]) -> None:
        if not item_ids:
            return

        async with new_session() as session:
            await session.execute(
                delete(cls.model).where(
                    cls.model.user_id == user_id,
                    cls.model.id.in_(item_ids),
                )
            )
            await session.commit()
