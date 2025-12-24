from typing import Type
from sqlalchemy import delete, insert, select, text, update
from app.database import Base, new_session



class BaseDAO():
    """
    Базовый класс для работы с БД.

    Представляет собой общие методы для всех моделей.
    """
    model: Type[Base] = None


    @classmethod
    async def find_one_or_none(cls, **filter_by) -> Base | None:
        """Находит 1 запись в БД по фильтрам.
        
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
        """Добавляет новую запись в БД.

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
        """Добавляет новую запись в БД и возвращает созданный объект.

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
        

    @classmethod
    async def update(cls, filter_by: dict, **values):
        """Изменяет уже существующие данные в таблице на новые.

        **Параметры:**
            - `filter_by`: данные поиска.
            - `values`: данные для замены.

        **Результат:**
            - `Измененный пользователь`
        """
        async with new_session() as session:
            query = update(cls.model).filter_by(**filter_by).values(**values).returning(cls.model)
            res = await session.execute(query)
            await session.commit()
            return res.scalar_one_or_none()
        

    @classmethod
    async def add_bulk(cls, data: list[dict]):
        """Добавляет много записей в БД транзакцией.

        **Параметры:**
            - `data`: список из словарей. Набор параметров для вставки.
        """
        async with new_session() as session:
            try:
                async with session.begin():
                    query = insert(cls.model)
                    res = await session.execute(query, data)
            except Exception as e:
                print(f"Ошибка при массовой вставке")
                raise e
            

    @classmethod
    async def delete_bulk(cls) -> None:
        """Удаляет все данные из таблицы сбрасывая индексы.

        **Результат:**
            - `None`.  
        """
        async with new_session() as session:
            await session.execute(text(f"TRUNCATE TABLE {cls.model.__tablename__} RESTART IDENTITY CASCADE"))
            await session.commit()

    @classmethod
    async def get_all(cls):
        """Возвращает все данные из бд.

        **Результат:**
            - `Объекты модели списком`.  
        """
        async with new_session() as session:
            query = select(cls.model)
            res = await session.execute(query)
            return res.scalars().all()
        

    @classmethod
    async def get_all_by(cls, **filter_by):
        """Возвращает все данные из бд по фильтру.

        **Результат:**
            - `Объекты модели списком`.  
        """
        async with new_session() as session:
            query = select(cls.model).filter_by(**filter_by)
            res = await session.execute(query)
            return res.scalars().all()