# -*- coding: utf-8 -*-
"""
Зависимости FastAPI
"""

from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.models.user import User
from src.core.exceptions import AppException

# Схема OAuth2 - auto_error=False делает токен опциональным
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
) -> User:
    """
    Получение текущего пользователя из токена.

    Для режима разработки (MVP/демо):
    - Если токен есть — проверяем и возвращаем пользователя
    - Если токена нет — возвращаем первого активного пользователя (dev режим)
    """
    # Если токен предоставлен, можно добавить проверку JWT (в будущем)
    # Сейчас для MVP просто игнорируем токен и возвращаем первого пользователя

    result = await db.execute(select(User).where(User.is_active == True).limit(1))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Нет активных пользователей в БД. Запустите seeder.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_optional(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
) -> User | None:
    """
    Получение текущего пользователя (опционально).

    Если токен не предоставлен, возвращает None.
    """
    if token is None:
        return None

    try:
        return await get_current_user(db, token)
    except HTTPException:
        return None


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Проверка на администратора.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется права администратора",
        )
    return current_user


async def get_current_engineer_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Проверка на инженера.
    """
    if not current_user.is_engineer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется права инженера",
        )
    return current_user


# Типовые аннотации
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = User
CurrentAdmin = Annotated[User, Depends(get_current_admin_user)]
CurrentEngineer = Annotated[User, Depends(get_current_engineer_user)]
