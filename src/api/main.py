# -*- coding: utf-8 -*-
"""
Главный файл FastAPI приложения
"""

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.core.database import init_db, dispose_db
from src.core.logging import setup_logging, get_logger
from src.api.router import api_router

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения.
    """
    # Инициализация
    setup_logging()
    logger.info("Запуск приложения Инженерный ИскИн...")
    
    # Инициализация БД
    await init_db()
    logger.info("База данных инициализирована")
    
    yield
    
    # Завершение
    await dispose_db()
    logger.info("Приложение остановлено")


# Создание приложения
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Система автоматизации эксплуатации зданий на основе ML",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Настройка middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }


def run():
    """Запуск сервера разработки"""
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
