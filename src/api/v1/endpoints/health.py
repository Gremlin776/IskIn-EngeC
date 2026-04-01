# -*- coding: utf-8 -*-
"""
Эндпоинт проверки работоспособности
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.core.config import get_settings
from src.api.v1.schemas.common import HealthResponse
from src.api.deps import get_db

router = APIRouter()
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Проверка состояния API и базы данных"""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        database=db_status,
    )
