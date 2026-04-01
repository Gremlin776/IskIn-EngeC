# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date

import pytest

from src.core.exceptions import NotFoundException, ValidationException
from src.services.repair_service import RepairService


@pytest.mark.asyncio
async def test_create_request_success(db_session, seed_data):
    """Создание заявки с валидными данными."""
    service = RepairService(db_session)

    request = await service.create_request(
        premise_id=seed_data["premise"].id,
        user_id=seed_data["user"].id,
        title="Течёт кран",
        description="Нужно заменить прокладку",
        repair_type_id=seed_data["repair_type"].id,
        priority="high",
    )

    assert request.id is not None
    assert request.status == "new"
    assert request.request_number.startswith("REP-")


@pytest.mark.asyncio
async def test_create_request_invalid_type_raises(db_session, seed_data):
    """Ошибка при создании заявки с несуществующим типом ремонта."""
    service = RepairService(db_session)

    with pytest.raises(NotFoundException):
        await service.create_request(
            premise_id=seed_data["premise"].id,
            user_id=seed_data["user"].id,
            title="Неверный тип",
            description="Проверка ошибки",
            repair_type_id=999999,
        )


@pytest.mark.asyncio
async def test_update_request_completed_sets_date(db_session, seed_data):
    """При статусе completed должна выставляться дата завершения."""
    service = RepairService(db_session)

    request = await service.create_request(
        premise_id=seed_data["premise"].id,
        user_id=seed_data["user"].id,
        title="Заменить лампу",
        description="Лампа перегорела",
    )

    updated = await service.update_request(request.id, status="completed")
    assert updated is not None
    assert updated.completed_date == date.today()


@pytest.mark.asyncio
async def test_update_request_invalid_status_raises(db_session, seed_data):
    """Ошибка при недопустимом статусе."""
    service = RepairService(db_session)

    request = await service.create_request(
        premise_id=seed_data["premise"].id,
        user_id=seed_data["user"].id,
        title="Проверка статуса",
        description="Недопустимый статус",
    )

    with pytest.raises(ValidationException):
        await service.update_request(request.id, status="bad_status")


@pytest.mark.asyncio
async def test_add_comment_success(db_session, seed_data):
    """Добавление комментария к заявке."""
    service = RepairService(db_session)

    request = await service.create_request(
        premise_id=seed_data["premise"].id,
        user_id=seed_data["user"].id,
        title="Шум в вентиляции",
        description="Сильный шум",
    )

    comment = await service.add_comment(
        request_id=request.id,
        user_id=seed_data["user"].id,
        comment_text="Проверить фильтры",
    )

    assert comment.id is not None
    assert comment.user_id == seed_data["user"].id
    assert comment.repair_request_id == request.id


@pytest.mark.asyncio
async def test_get_stats_counts_requests(db_session, seed_data):
    """Проверка статистики по заявкам."""
    service = RepairService(db_session)

    req1 = await service.create_request(
        premise_id=seed_data["premise"].id,
        user_id=seed_data["user"].id,
        title="Заявка 1",
        description="Описание 1",
        priority="low",
    )
    req2 = await service.create_request(
        premise_id=seed_data["premise"].id,
        user_id=seed_data["user"].id,
        title="Заявка 2",
        description="Описание 2",
        priority="high",
    )

    # Обновляем статус второй заявки
    await service.update_request(req2.id, status="in_progress")

    stats = await service.get_stats()
    assert stats["total"] >= 2
    assert "new" in stats["by_status"] or "in_progress" in stats["by_status"]
