# -*- coding: utf-8 -*-
"""
E2E тесты полного цикла ключевых сценариев.
"""

from __future__ import annotations

import io
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from sqlalchemy import select

from src.api.router import api_router
from src.api.deps import get_db, get_current_user
from src.models.defect import DefectClass, DetectedDefect, InspectionPhoto


@pytest.fixture()
def test_app() -> FastAPI:
    """Отдельное приложение для E2E тестов."""
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    return app


@pytest.fixture()
async def async_client(test_app: FastAPI, db_session, seed_data):
    """Асинхронный клиент с подменой зависимостей."""

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return seed_data["user"]

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=test_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=True,
    ) as client:
        yield client

    test_app.dependency_overrides.clear()


@pytest.fixture()
def building_payload():
    """Данные для создания здания."""
    return {
        "name": "Здание E2E",
        "address": "г. Астрахань, ул. Тестовая, 1",
        "building_type": "office",
        "year_built": 2001,
        "floors": 5,
        "total_area": 1234.5,
    }


@pytest.fixture()
def premise_payload():
    """Данные для создания помещения."""
    return {
        "floor": 2,
        "room_number": "204",
        "room_name": "Тестовая комната",
        "room_type": "office",
        "area": 55.5,
    }


@pytest.fixture()
def repair_request_payload(seed_data):
    """Данные для создания ремонтной заявки."""
    return {
        "title": "Требуется ремонт вентиляции",
        "description": "Шум и вибрация при работе вентиляции в помещении.",
        "priority": "medium",
        "repair_type_id": seed_data["repair_type"].id,
    }


@pytest.fixture()
def meter_payload(seed_data):
    """Данные для создания счётчика."""
    return {
        "meter_number": "E2E-0001",
        "premise_id": seed_data["premise"].id,
        "meter_type_id": seed_data["meter_type"].id,
        "manufacturer": "TestCorp",
        "model": "M-100",
        "serial_number": "SN-12345",
    }


@pytest.fixture()
def meter_reading_payload():
    """Данные для добавления показания."""
    return {
        "reading_value": "123.45",
        "notes": "Плановое показание",
    }


@pytest.fixture()
def inspection_payload(seed_data):
    """Данные для создания обследования."""
    return {
        "building_id": seed_data["building"].id,
        "inspection_type": "routine",
        "notes": "Плановый осмотр",
    }


@pytest.mark.asyncio
async def test_full_repair_workflow(
    async_client: AsyncClient,
    building_payload,
    premise_payload,
    repair_request_payload,
):
    """Сценарий 1 — Полный цикл ремонта."""

    # 1. POST /buildings → создать здание
    create_building = await async_client.post("/api/v1/buildings", json=building_payload)
    assert create_building.status_code == 201
    building = create_building.json()
    assert "id" in building

    # 2. POST /premises → создать помещение
    premise_payload["building_id"] = building["id"]
    create_premise = await async_client.post("/api/v1/premises", json=premise_payload)
    assert create_premise.status_code == 201
    premise = create_premise.json()
    assert premise["building_id"] == building["id"]

    # 3. POST /repair/requests → создать заявку
    repair_request_payload["premise_id"] = premise["id"]
    create_request = await async_client.post(
        "/api/v1/repair/requests",
        json=repair_request_payload,
    )
    assert create_request.status_code == 201
    request_data = create_request.json()
    assert request_data["premise_id"] == premise["id"]

    # 4. PATCH /repair/requests/{id}/status → изменить статус
    update_status = await async_client.patch(
        f"/api/v1/repair/requests/{request_data['id']}/status",
        json={"status": "in_progress"},
    )
    assert update_status.status_code == 200
    assert update_status.json()["status"] == "in_progress"

    # 5. Проверить статистику GET /repair/stats/summary
    stats = await async_client.get("/api/v1/repair/stats/summary")
    assert stats.status_code == 200
    stats_data = stats.json()
    assert "total" in stats_data
    assert "by_status" in stats_data
    assert "by_priority" in stats_data


@pytest.mark.asyncio
async def test_meter_accounting_workflow(
    async_client: AsyncClient,
    meter_payload,
    meter_reading_payload,
):
    """Сценарий 2 — Учёт счётчиков."""

    # 1. POST /meters → создать счётчик
    create_meter = await async_client.post("/api/v1/meters", json=meter_payload)
    assert create_meter.status_code == 201
    meter = create_meter.json()
    assert meter["meter_number"] == meter_payload["meter_number"]

    # 2. POST /meters/{id}/readings → добавить показание
    add_reading = await async_client.post(
        f"/api/v1/meters/{meter['id']}/readings",
        json=meter_reading_payload,
    )
    assert add_reading.status_code == 201
    reading = add_reading.json()
    assert reading["meter_id"] == meter["id"]

    # 3. GET /meters/{id}/readings → проверить историю
    readings = await async_client.get(f"/api/v1/meters/{meter['id']}/readings")
    assert readings.status_code == 200
    readings_data = readings.json()
    assert isinstance(readings_data, list)
    assert len(readings_data) >= 1

    # 4. GET /meters/stats/consumption → проверить статистику
    stats = await async_client.get(
        "/api/v1/meters/stats/consumption",
        params={"meter_id": meter["id"], "months": 6},
    )
    assert stats.status_code == 200
    stats_data = stats.json()
    assert "meter" in stats_data
    assert "consumption" in stats_data


@pytest.mark.asyncio
async def test_building_inspection_workflow(
    async_client: AsyncClient,
    db_session,
    inspection_payload,
    seed_data,
):
    """Сценарий 3 — Обследование здания."""

    # 1. POST /defects/inspections → создать обследование
    create_inspection = await async_client.post(
        "/api/v1/defects/inspections",
        json=inspection_payload,
    )
    assert create_inspection.status_code == 201
    inspection = create_inspection.json()
    assert inspection["building_id"] == inspection_payload["building_id"]

    # 2. POST /defects/inspections/{id}/photos → загрузить фото
    fake_image = io.BytesIO(b"fake-image-bytes")
    upload_photo = await async_client.post(
        f"/api/v1/defects/inspections/{inspection['id']}/photos",
        files={"file": ("defect.jpg", fake_image, "image/jpeg")},
    )
    assert upload_photo.status_code == 201

    # Находим ID фото в БД (эндпоинт возвращает объект без response_model)
    photo_result = await db_session.execute(
        select(InspectionPhoto)
        .where(InspectionPhoto.inspection_id == inspection["id"])
    )
    photo = photo_result.scalars().first()
    assert photo is not None

    # Создаём класс дефекта и сам дефект вручную, чтобы не запускать YOLO
    defect_class = DefectClass(
        name="Трещина",
        code="crack",
        yolo_class_id=0,
        severity_level=3,
        color="#FF0000",
    )
    db_session.add(defect_class)
    await db_session.flush()

    defect = DetectedDefect(
        inspection_id=inspection["id"],
        photo_id=photo.id,
        defect_class_id=defect_class.id,
        confidence=0.85,
        severity="medium",
        status="detected",
    )
    db_session.add(defect)
    await db_session.commit()
    await db_session.refresh(defect)

    # 3. GET /defects/inspections/{id}/defects → получить дефекты
    defects = await async_client.get(
        f"/api/v1/defects/inspections/{inspection['id']}/defects"
    )
    assert defects.status_code == 200
    defects_data = defects.json()
    assert isinstance(defects_data, list)
    assert len(defects_data) >= 1

    defect_id = defects_data[0]["id"]

    # 4. PUT /defects/{id}/review → подтвердить дефект
    review = await async_client.put(
        f"/api/v1/defects/{defect_id}/review",
        json={"status": "reviewed", "review_notes": "Подтверждено"},
    )
    assert review.status_code == 200
    assert review.json()["status"] == "reviewed"
