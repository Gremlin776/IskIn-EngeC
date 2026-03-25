from __future__ import annotations

"""
Сервис для генерации отчётов
"""

import uuid
from datetime import datetime, date, timedelta
from typing import Any
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.report import Report, ReportTemplate, ReportEntity
from src.core.exceptions import NotFoundException, APIException
from src.core.logging import get_logger
from src.integrations.llm_client import LLMClient

logger = get_logger(__name__)


class ReportService:
    """
    Сервис для генерации отчётов и актов.
    
    Бизнес-логика:
    - Генерация номера отчёта
    - Сбор данных из БД
    - Генерация текста через LLM
    - Сохранение отчёта
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.llm_client = LLMClient()

    def _generate_report_number(self) -> str:
        """Генерация уникального номера отчёта"""
        timestamp = datetime.now().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"RPT-{timestamp}-{unique_id}"

    async def create_report(
        self,
        user_id: int,
        title: str,
        report_type: str,
        template_id: int | None = None,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> Report:
        """Создание черновика отчёта"""
        report = await self._create_report_entity(
            user_id=user_id,
            title=title,
            report_type=report_type,
            template_id=template_id,
            period_start=period_start,
            period_end=period_end,
            status="draft",
        )

        logger.info(f"Создан отчёт: {report.report_number}")
        return report

    async def _create_report_entity(
        self,
        user_id: int,
        title: str,
        report_type: str,
        **kwargs,
    ) -> Report:
        """Создание объекта отчёта в БД"""
        from sqlalchemy import insert
        
        # Прямая вставка для обхода валидации
        stmt = insert(Report).values(
            report_number=self._generate_report_number(),
            user_id=user_id,
            title=title,
            report_type=report_type,
            **kwargs,
        ).returning(Report)
        
        result = await self.session.execute(stmt)
        report = result.scalar_one()
        await self.session.flush()
        return report

    async def generate_repair_report(
        self,
        user_id: int,
        period_start: date,
        period_end: date,
        building_id: int | None = None,
    ) -> Report:
        """
        Генерация отчёта по ремонтным работам.
        
        Собирает:
        - Список заявок за период
        - Статистику по статусам
        - Информацию о затратах
        """
        from sqlalchemy import select, func
        from src.models.repair import RepairRequest
        
        # Сбор данных
        query = select(RepairRequest).where(
            RepairRequest.created_at >= datetime.combine(period_start, datetime.min.time()),
            RepairRequest.created_at <= datetime.combine(period_end, datetime.max.time()),
        )
        
        if building_id:
            from src.models.building import Premise
            query = query.join(Premise).where(Premise.building_id == building_id)
        
        result = await self.session.execute(query)
        repairs = result.scalars().all()

        # Формирование промпта для LLM
        prompt = self._build_repair_report_prompt(repairs, period_start, period_end)
        
        # Генерация через LLM
        content = await self.llm_client.generate_report(prompt)

        # Создание отчёта
        report = await self._create_report_entity(
            user_id=user_id,
            title=f"Отчёт по ремонтным работам ({period_start} - {period_end})",
            report_type="repair",
            period_start=period_start,
            period_end=period_end,
            content=content,
            status="completed",
        )

        # Добавление связей
        for repair in repairs:
            await self._add_report_entity(report.id, "repair_request", repair.id)

        logger.info(f"Сгенерирован отчёт по ремонтам: {report.report_number}")
        return report

    async def generate_inspection_report(
        self,
        user_id: int,
        inspection_id: int,
    ) -> Report:
        """
        Генерация отчёта по обследованию.
        
        Собирает:
        - Информацию об обследовании
        - Список дефектов
        - Фотографии
        """
        from src.models.defect import Inspection, DetectedDefect
        
        # Получение обследования
        result = await self.session.execute(
            select(Inspection).where(Inspection.id == inspection_id)
        )
        inspection = result.scalar_one_or_none()
        
        if inspection is None:
            raise NotFoundException("Обследование", inspection_id)

        # Получение дефектов
        result = await self.session.execute(
            select(DetectedDefect)
            .where(DetectedDefect.inspection_id == inspection_id)
        )
        defects = result.scalars().all()

        # Формирование промпта
        prompt = self._build_inspection_report_prompt(inspection, defects)
        
        # Генерация через LLM
        content = await self.llm_client.generate_report(prompt)

        # Создание отчёта
        report = await self._create_report_entity(
            user_id=user_id,
            title=f"Отчёт по обследованию {inspection.inspection_number}",
            report_type="inspection",
            period_start=inspection.inspection_date,
            period_end=inspection.inspection_date,
            content=content,
            status="completed",
        )

        await self._add_report_entity(report.id, "inspection", inspection_id)

        logger.info(f"Сгенерирован отчёт по обследованию: {report.report_number}")
        return report

    async def generate_monthly_report(
        self,
        user_id: int,
        year: int,
        month: int,
    ) -> Report:
        """
        Генерация ежемесячного сводного отчёта.
        """
        period_start = date(year, month, 1)
        if month == 12:
            period_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            period_end = date(year, month + 1, 1) - timedelta(days=1)

        # Сбор данных по всем модулям
        prompt = await self._build_monthly_report_prompt(
            period_start, period_end
        )
        
        content = await self.llm_client.generate_report(prompt)

        report = await self._create_report_entity(
            user_id=user_id,
            title=f"Ежемесячный отчёт ({year}-{month:02d})",
            report_type="monthly",
            period_start=period_start,
            period_end=period_end,
            content=content,
            status="completed",
        )

        logger.info(f"Сгенерирован ежемесячный отчёт: {report.report_number}")
        return report

    async def generate_custom_report(
        self,
        user_id: int,
        title: str,
        prompt: str,
        report_type: str = "general",
    ) -> Report:
        """
        Генерация кастомного отчёта по пользовательскому промпту.
        """
        content = await self.llm_client.generate_report(prompt)

        report = await self._create_report_entity(
            user_id=user_id,
            title=title,
            report_type=report_type,
            content=content,
            status="completed",
        )

        logger.info(f"Сгенерирован кастомный отчёт: {report.report_number}")
        return report

    def _build_repair_report_prompt(
        self,
        repairs: list,
        period_start: date,
        period_end: date,
    ) -> str:
        """Построение промпта для отчёта по ремонтам"""
        total = len(repairs)
        completed = sum(1 for r in repairs if r.status == "completed")
        total_cost = sum(r.cost or 0 for r in repairs)

        return f"""
Создай отчёт по ремонтным работам за период с {period_start} по {period_end}.

Данные:
- Всего заявок: {total}
- Завершено: {completed}
- Общая стоимость: {total_cost:.2f} руб.

Статусы:
{self._format_repairs_stats(repairs)}

Сформируй структурированный отчёт с выводами и рекомендациями.
"""

    def _format_repairs_stats(self, repairs: list) -> str:
        """Форматирование статистики ремонтов"""
        from collections import Counter
        status_counts = Counter(r.status for r in repairs)
        return "\n".join(f"- {status}: {count}" for status, count in status_counts.items())

    def _build_inspection_report_prompt(
        self,
        inspection: Inspection,
        defects: list,
    ) -> str:
        """Построение промпта для отчёта по обследованию"""
        critical = sum(1 for d in defects if d.severity == "critical")
        high = sum(1 for d in defects if d.severity == "high")

        return f"""
Создай отчёт по обследованию {inspection.inspection_number}.

Объект: {inspection.building.name if inspection.building else 'Н/Д'}
Дата: {inspection.inspection_date}
Тип: {inspection.inspection_type}

Найдено дефектов: {len(defects)}
- Критические: {critical}
- Высокой серьёзности: {high}

{inspection.notes or 'Примечаний нет.'}

Сформируй профессиональный отчёт инженера-строителя.
"""

    async def _build_monthly_report_prompt(
        self,
        period_start: date,
        period_end: date,
    ) -> str:
        """Построение промпта для ежемесячного отчёта"""
        from sqlalchemy import select, func
        from src.models.repair import RepairRequest
        from src.models.meter import MeterReading
        from src.models.defect import DetectedDefect

        # Статистика ремонтов
        repair_result = await self.session.execute(
            select(func.count()).select_from(RepairRequest).where(
                RepairRequest.created_at >= datetime.combine(period_start, datetime.min.time()),
                RepairRequest.created_at <= datetime.combine(period_end, datetime.max.time()),
            )
        )
        repair_count = repair_result.scalar() or 0

        # Статистика дефектов
        defect_result = await self.session.execute(
            select(func.count()).select_from(DetectedDefect).where(
                DetectedDefect.created_at >= datetime.combine(period_start, datetime.min.time()),
                DetectedDefect.created_at <= datetime.combine(period_end, datetime.max.time()),
            )
        )
        defect_count = defect_result.scalar() or 0

        return f"""
Создай ежемесячный сводный отчёт за период с {period_start} по {period_end}.

Ключевые метрики:
- Ремонтных заявок: {repair_count}
- Детектированных дефектов: {defect_count}

Сформируй структурированный отчёт для руководства с анализом и рекомендациями.
"""

    async def _add_report_entity(
        self,
        report_id: int,
        entity_type: str,
        entity_id: int,
    ) -> None:
        """Добавление связи отчёта с объектом"""
        from sqlalchemy import insert
        
        stmt = insert(ReportEntity).values(
            report_id=report_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        await self.session.execute(stmt)

    async def get_report(self, report_id: int) -> Report | None:
        """Получение отчёта"""
        from sqlalchemy import select
        
        result = await self.session.execute(
            select(Report).where(Report.id == report_id)
        )
        return result.scalar_one_or_none()

    async def delete_report(self, report_id: int) -> bool:
        """Удаление отчёта"""
        report = await self.get_report(report_id)
        if report is None:
            return False
        
        await self.session.delete(report)
        await self.session.flush()
        return True


# Импорт для расчёта дат
from datetime import timedelta  # noqa: E402
