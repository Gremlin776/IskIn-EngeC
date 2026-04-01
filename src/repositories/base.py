# -*- coding: utf-8 -*-
"""
Базовый репозиторий с CRUD операциями
"""

from typing import Generic, TypeVar
from sqlalchemy import select, func, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """
    Базовый репозиторий с основными CRUD операциями.
    
    Использование:
        class UserRepository(BaseRepository[User]):
            model = User
    """

    model: type[ModelType]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int) -> ModelType | None:
        """Получить объект по ID"""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_or_raise(self, id: int) -> ModelType:
        """Получить объект по ID или выбросить исключение"""
        obj = await self.get(id)
        if obj is None:
            raise ValueError(f"{self.model.__name__} с ID {id} не найден")
        return obj

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by=None,
    ) -> list[ModelType]:
        """Получить список объектов"""
        query = select(self.model)
        
        if order_by is not None:
            query = query.order_by(order_by)
        
        query = query.offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, **kwargs) -> ModelType:
        """Создать новый объект"""
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update(self, id: int, **kwargs) -> ModelType | None:
        """Обновить объект"""
        obj = await self.get(id)
        if obj is None:
            return None
        
        for key, value in kwargs.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, id: int) -> bool:
        """Удалить объект"""
        obj = await self.get(id)
        if obj is None:
            return False
        
        await self.session.delete(obj)
        await self.session.flush()
        return True

    async def count(self) -> int:
        """Получить количество объектов"""
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar() or 0

    async def exists(self, id: int) -> bool:
        """Проверить существование объекта"""
        result = await self.session.execute(
            select(func.count()).select_from(self.model).where(self.model.id == id)
        )
        return (result.scalar() or 0) > 0
