# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.api.router import api_router
from src.api.deps import get_db, get_current_user
from src.models.base import Base
from src.models.user import User
from src.models.building import Building, Premise
from src.models.repair import RepairType
from src.models.meter import MeterType


# Отдельное приложение для тестов без lifespan (чтобы не трогать реальную БД).
test_app = FastAPI()
test_app.include_router(api_router, prefix="/api/v1")


@pytest.fixture(scope="session")
def event_loop():
    """Глобальный event loop для pytest-asyncio."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def async_engine():
    """Тестовый движок SQLite в памяти."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture()
async def db_session(async_engine) -> AsyncSession:
    """Сессия БД на тест."""
    session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture()
async def seed_data(db_session: AsyncSession):
    """Базовые данные для тестов."""
    user = User(
        username="tester",
        email="tester@example.com",
        password_hash="hash",
        full_name="Тестовый Пользователь",
        role="admin",
        is_active=True,
    )
    building = Building(name="Тестовое здание", address="Тестовый адрес")
    premise = Premise(building=building, floor=1, room_number="101")
    repair_type = RepairType(name="Тестовый ремонт", code="TEST-001", priority=1)
    meter_type = MeterType(name="Вода", code="WTR", unit="м³")

    db_session.add_all([user, building, premise, repair_type, meter_type])
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(premise)
    await db_session.refresh(repair_type)
    await db_session.refresh(meter_type)

    return {
        "user": user,
        "building": building,
        "premise": premise,
        "repair_type": repair_type,
        "meter_type": meter_type,
    }


@pytest.fixture()
def client(db_session: AsyncSession, seed_data):
    """Тестовый клиент FastAPI с подменой зависимостей."""

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return seed_data["user"]

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(test_app) as c:
        yield c

    test_app.dependency_overrides.clear()
