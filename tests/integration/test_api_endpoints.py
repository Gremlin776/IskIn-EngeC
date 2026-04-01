# -*- coding: utf-8 -*-
from __future__ import annotations


def test_health_check_ok(client):
    """Проверка health эндпоинта."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_create_building(client):
    """Создание здания через API."""
    payload = {
        "name": "БЦ Тест",
        "address": "г. Тест, ул. Пример, 1",
        "building_type": "office",
        "year_built": 2005,
        "floors": 5,
        "total_area": 1500.5,
    }
    response = client.post("/api/v1/buildings/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["address"] == payload["address"]


def test_get_buildings_list(client):
    """Получение списка зданий."""
    response = client.get("/api/v1/buildings/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_building_by_id(client, seed_data):
    """Получение здания по ID."""
    building_id = seed_data["building"].id
    response = client.get(f"/api/v1/buildings/{building_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == building_id


def test_update_building(client, seed_data):
    """Обновление данных здания."""
    building_id = seed_data["building"].id
    payload = {"name": "Обновлённое здание"}
    response = client.put(f"/api/v1/buildings/{building_id}", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == payload["name"]


def test_delete_building_marks_inactive(client, seed_data):
    """Удаление здания переводит его в неактивное состояние."""
    building_id = seed_data["building"].id
    response = client.delete(f"/api/v1/buildings/{building_id}")
    assert response.status_code == 204

    # Проверяем, что здание стало неактивным
    response = client.get(f"/api/v1/buildings/{building_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False


def test_building_stats(client, seed_data):
    """Статистика по зданию."""
    building_id = seed_data["building"].id
    response = client.get(f"/api/v1/buildings/{building_id}/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["building_id"] == building_id
    assert data["premises_count"] >= 1
