# -*- coding: utf-8 -*-
"""
Базовый сервис
"""

from typing import Generic, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import BaseModel
from src.repositories.base import BaseRepository

ModelType = TypeVar("ModelType", bound=BaseModel)
RepositoryType = TypeVar("RepositoryType", bound=BaseRepository)


class BaseService(Generic[ModelType, RepositoryType]):
    """
    Базовый класс сервиса.
    
    Использование:
        class UserService(BaseService[User, UserRepository]):
            ...
    """

    repository_class: type[RepositoryType]

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = self.repository_class(session)
