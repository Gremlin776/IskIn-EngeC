"""
Сервис для управления ремонтными работами
"""

import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Any
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.repair import RepairRequest, RepairPhoto, RepairComment
from src.repositories.repair_repository import RepairRepository, RepairTypeRepository
from src.core.exceptions import NotFoundException, ValidationException
from src.core.logging import get_logger

logger = get_logger(__name__)


class RepairService:
    """
    Сервис для управления заявками на ремонт.
    
    Бизнес-логика:
    - Генерация номера заявки
    - Валидация статусов
    - Управление фото и комментариями
    - Статистика
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = RepairRepository(session)
        self.type_repository = RepairTypeRepository(session)

    def _generate_request_number(self) -> str:
        """Генерация уникального номера заявки"""
        timestamp = datetime.now().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"REP-{timestamp}-{unique_id}"

    async def create_request(
        self,
        premise_id: int,
        user_id: int,
        title: str,
        description: str,
        repair_type_id: int | None = None,
        priority: str = "medium",
        scheduled_date: date | None = None,
        **kwargs,
    ) -> RepairRequest:
        """Создание новой заявки на ремонт"""
        # Валидация типа ремонта
        if repair_type_id is not None:
            repair_type = await self.type_repository.get(repair_type_id)
            if repair_type is None:
                raise NotFoundException("Тип ремонта", repair_type_id)

        request = await self.repository.create(
            request_number=self._generate_request_number(),
            premise_id=premise_id,
            user_id=user_id,
            repair_type_id=repair_type_id,
            title=title,
            description=description,
            priority=priority,
            scheduled_date=scheduled_date,
            status="new",
            **kwargs,
        )

        logger.info(f"Создана заявка на ремонт: {request.request_number}")
        return request

    async def get_request(self, request_id: int) -> RepairRequest | None:
        """Получение заявки с отношениями"""
        return await self.repository.get_with_relations(request_id)

    async def update_request(
        self,
        request_id: int,
        **updates: Any,
    ) -> RepairRequest | None:
        """Обновление заявки"""
        # Запрещаем изменять номер заявки
        updates.pop("request_number", None)
        
        # Валидация статуса
        if "status" in updates:
            valid_statuses = {"new", "in_progress", "completed", "cancelled"}
            if updates["status"] not in valid_statuses:
                raise ValidationException(
                    f"Неверный статус. Допустимые: {valid_statuses}"
                )
            
            # Автоматическая установка даты завершения
            if updates["status"] == "completed":
                updates["completed_date"] = date.today()

        return await self.repository.update(request_id, **updates)

    async def delete_request(self, request_id: int) -> bool:
        """Удаление заявки"""
        return await self.repository.delete(request_id)

    async def add_photo(
        self,
        request_id: int,
        file_path: Path,
        file_name: str,
        description: str | None = None,
        is_main: bool = False,
    ) -> RepairPhoto:
        """Добавление фото к заявке"""
        # Проверка существования заявки
        request = await self.repository.get(request_id)
        if request is None:
            raise NotFoundException("Заявка на ремонт", request_id)

        return await self.repository.add_photo(
            repair_request_id=request_id,
            file_path=str(file_path),
            file_name=file_name,
            description=description,
            is_main=is_main,
            file_size=file_path.stat().st_size if file_path.exists() else None,
        )

    async def add_comment(
        self,
        request_id: int,
        user_id: int,
        comment_text: str,
    ) -> RepairComment:
        """Добавление комментария к заявке"""
        return await self.repository.add_comment(
            repair_request_id=request_id,
            user_id=user_id,
            comment_text=comment_text,
        )

    async def get_stats(self) -> dict[str, Any]:
        """Получение сводной статистики"""
        status_stats = await self.repository.get_stats_by_status()
        priority_stats = await self.repository.get_stats_by_priority()
        total = await self.repository.count()

        return {
            "total": total,
            "by_status": status_stats,
            "by_priority": priority_stats,
        }

    async def get_requests_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[RepairRequest]:
        """Получение заявок по статусу"""
        return await self.repository.get_by_status(status, skip, limit)

    async def get_requests_by_premise(
        self,
        premise_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[RepairRequest]:
        """Получение заявок по помещению"""
        return await self.repository.get_by_premise(premise_id, skip, limit)
