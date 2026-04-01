# -*- coding: utf-8 -*-
"""
Репозиторий для учёта счётчиков
"""

from datetime import date
from decimal import Decimal
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.meter import (
    Meter,
    MeterReading,
    MeterType,
    OCRProcessingLog,
)
from src.repositories.base import BaseRepository


class MeterRepository(BaseRepository[Meter]):
    """Репозиторий для работы со счётчиками"""

    model = Meter

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_with_readings(self, id: int) -> Meter | None:
        """Получить счётчик с показаниями"""
        result = await self.session.execute(
            select(Meter)
            .options(
                selectinload(Meter.readings).order_by(MeterReading.reading_date.desc()),
                selectinload(Meter.meter_type),
                selectinload(Meter.premise),
            )
            .where(Meter.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_premise(
        self,
        premise_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Meter]:
        """Получить счётчики по помещению"""
        result = await self.session.execute(
            select(Meter)
            .options(selectinload(Meter.meter_type))
            .where(Meter.premise_id == premise_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_type(
        self,
        meter_type_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Meter]:
        """Получить счётчики по типу"""
        result = await self.session.execute(
            select(Meter)
            .where(Meter.meter_type_id == meter_type_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_due_verification(
        self,
        days_ahead: int = 30,
    ) -> list[Meter]:
        """Получить счётчики с предстоящей поверкой"""
        from sqlalchemy import text
        
        result = await self.session.execute(
            select(Meter).where(
                and_(
                    Meter.next_verification.isnot(None),
                    Meter.next_verification <= func.date("now", f"+{days_ahead} days"),
                    Meter.is_active == True,
                )
            )
        )
        return list(result.scalars().all())

    async def add_reading(
        self,
        meter_id: int,
        reading_value: Decimal,
        reading_date: date,
        **kwargs,
    ) -> MeterReading:
        """Добавить показание"""
        reading = MeterReading(
            meter_id=meter_id,
            reading_value=reading_value,
            reading_date=reading_date,
            **kwargs,
        )
        self.session.add(reading)
        await self.session.flush()
        await self.session.refresh(reading)
        return reading

    async def get_last_reading(self, meter_id: int) -> MeterReading | None:
        """Получить последнее показание"""
        result = await self.session.execute(
            select(MeterReading)
            .where(MeterReading.meter_id == meter_id)
            .order_by(MeterReading.reading_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_readings_period(
        self,
        meter_id: int,
        start_date: date,
        end_date: date,
    ) -> list[MeterReading]:
        """Получить показания за период"""
        result = await self.session.execute(
            select(MeterReading)
            .where(
                and_(
                    MeterReading.meter_id == meter_id,
                    MeterReading.reading_date >= start_date,
                    MeterReading.reading_date <= end_date,
                )
            )
            .order_by(MeterReading.reading_date)
        )
        return list(result.scalars().all())

    async def get_consumption_stats(
        self,
        meter_id: int,
        months: int = 6,
    ) -> list[dict]:
        """Получить статистику потребления"""
        result = await self.session.execute(
            select(
                func.strftime("%Y-%m", MeterReading.reading_date).label("month"),
                func.max(MeterReading.reading_value).label("max_value"),
                func.min(MeterReading.reading_value).label("min_value"),
            )
            .where(MeterReading.meter_id == meter_id)
            .group_by(func.strftime("%Y-%m", MeterReading.reading_date))
            .order_by(func.strftime("%Y-%m", MeterReading.reading_date).desc())
            .limit(months)
        )
        return [
            {"month": row[0], "max_value": float(row[1]), "min_value": float(row[2])}
            for row in result.all()
        ]


class MeterTypeRepository(BaseRepository[MeterType]):
    """Репозиторий для типов счётчиков"""

    model = MeterType

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_code(self, code: str) -> MeterType | None:
        """Получить тип по коду"""
        result = await self.session.execute(
            select(MeterType).where(MeterType.code == code)
        )
        return result.scalar_one_or_none()


class OCRProcessingLogRepository(BaseRepository[OCRProcessingLog]):
    """Репозиторий для логов OCR"""

    model = OCRProcessingLog

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def log_processing(
        self,
        original_image: str,
        status: str,
        **kwargs,
    ) -> OCRProcessingLog:
        """Записать лог обработки"""
        log_entry = OCRProcessingLog(
            original_image=original_image,
            status=status,
            **kwargs,
        )
        self.session.add(log_entry)
        await self.session.flush()
        await self.session.refresh(log_entry)
        return log_entry
