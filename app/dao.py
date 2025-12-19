from typing import Type
from sqlalchemy import insert, select
from app.database import Base, new_session



class BaseDAO():
    """
    Базовый класс для работы с БД.

    Представляет собой общие методы для всех моделей.
    """
    model: Type[Base] = None


    @classmethod
    async def find_one_or_none(cls, **filter_by) -> Base | None:
        """
        Находит 1 запись в БД по фильтрам.
        
        **Параметры:**
            - `**filter_by`: параметры поиска.

        **Результат:**
            - `Объект модели`, либо `None`, если запись не найдена.
        """
        async with new_session() as session:
            query = select(cls.model).filter_by(**filter_by)
            res = await session.execute(query)
            return res.scalar_one_or_none()
        
    @classmethod
    async def add(cls, **values) -> None:
        """
        Добавляет новую запись в БД.

        **Параметры:**
            - `values`: данные для вставки.

        **Результат:**
            - `None`.  
        """
        async with new_session() as session:
            query = insert(cls.model).values(**values)
            await session.execute(query)
            await session.commit()

    @classmethod
    async def add_and_return(cls, **values):
        """
        Добавляет новую запись в БД и возвращает созданный объект.

        **Параметры:**
            - `values`: данные для вставки.

        **Результат:**
            - `Объект указанной модели`.  
        """
        async with new_session() as session:
            query = insert(cls.model).values(**values).returning(cls.model)
            res = await session.execute(query)
            await session.commit()
            return res.scalar_one()