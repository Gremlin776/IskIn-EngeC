# -*- coding: utf-8 -*-
"""
Общие схемы API
"""

from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field
from datetime import datetime

T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    """Базовая модель ответа"""

    success: bool = True
    data: T | None = None
    message: str | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Модель пагинированного ответа"""

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class HealthResponse(BaseModel):
    """Ответ health check"""

    status: str = "healthy"
    version: str
    database: str = "connected"
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """Модель ошибки"""

    error: str
    detail: str | None = None
    code: str | None = None
