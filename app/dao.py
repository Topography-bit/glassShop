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
    async def find_one_or_none(cls, session=None, **filter_by) -> Base | None:
        """Находит 1 запись в БД по фильтрам.
        
        **Параметры:**
            - `**filter_by`: параметры поиска.

        **Результат:**
            - `Объект модели`, либо `None`, если запись не найдена.
        """
        query = select(cls.model).filter_by(**filter_by)
        if session is None:
            async with new_session() as session:
                res = await session.execute(query)
        else:
            res = await session.execute(query)

        return res.scalar_one_or_none()

    @classmethod
    async def add(cls, session=None, **values) -> None:
        """Добавляет новую запись в БД.

        **Параметры:**
            - `values`: данные для вставки.

        **Результат:**
            - `None`.  
        """
        query = insert(cls.model).values(**values)
        if session is None:
            async with new_session() as session:
                await session.execute(query)
                await session.commit()
        else:
            await session.execute(query)

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
    async def update(cls, filter_by: dict, session=None, **values):
        """Изменяет уже существующие данные в таблице на новые.

        **Параметры:**
            - `filter_by`: данные поиска.
            - `values`: данные для замены.

        **Результат:**
            - `Измененный пользователь`
        """
        query = update(cls.model).filter_by(**filter_by).values(**values).returning(cls.model)
        if session is None:
            async with new_session() as session:
                res = await session.execute(query)
                await session.commit()
        else:
            res = await session.execute(query)
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
        """
        async with new_session() as session:
            await session.execute(text(f"TRUNCATE TABLE {cls.model.__tablename__} RESTART IDENTITY CASCADE"))
            await session.commit()

    @classmethod
    async def get_all(cls, session=None):
        """Возвращает все данные из бд.

        **Результат:**
            - `Объекты модели списком`.  
        """
        query = select(cls.model)
        if session is None:
            async with new_session() as session:
                res = await session.execute(query)
        else:
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
        
    @classmethod
    async def delete_by(cls, **filter_by):
        """Удаляет все данные из бд по фильтру.
        """
        async with new_session() as session:
            query = delete(cls.model).filter_by(**filter_by)
            await session.execute(query)
            await session.commit()

    @classmethod
    async def make_all_unactive(cls, session=None):
        """Делает все в таблице неактивным.
        """
        if session is None:
            async with new_session() as session:
                await session.execute(update(cls.model).values(is_active=False))
                await session.commit()
        else:
            await session.execute(update(cls.model).values(is_active=False))
                