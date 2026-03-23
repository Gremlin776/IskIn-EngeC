"""
Сервис для учёта показаний счётчиков
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.meter import Meter, MeterReading, OCRProcessingLog
from src.repositories.meter_repository import (
    MeterRepository,
    MeterTypeRepository,
    OCRProcessingLogRepository,
)
from src.core.exceptions import NotFoundException, ValidationException, MLException
from src.core.logging import get_logger
from src.ml.ocr.engine import OCREngine

logger = get_logger(__name__)


class MeterService:
    """
    Сервис для управления счётчиками и показаниями.
    
    Бизнес-логика:
    - Добавление показаний
    - OCR обработка фото
    - Расчёт потребления
    - Проверка аномалий
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = MeterRepository(session)
        self.type_repository = MeterTypeRepository(session)
        self.ocr_log_repository = OCRProcessingLogRepository(session)
        self.ocr_engine = OCREngine()

    async def create_meter(
        self,
        meter_number: str,
        premise_id: int,
        meter_type_id: int,
        **kwargs,
    ) -> Meter:
        """Создание счётчика"""
        # Валидация типа счётчика
        meter_type = await self.type_repository.get(meter_type_id)
        if meter_type is None:
            raise NotFoundException("Тип счётчика", meter_type_id)

        meter = await self.repository.create(
            meter_number=meter_number,
            premise_id=premise_id,
            meter_type_id=meter_type_id,
            **kwargs,
        )

        logger.info(f"Создан счётчик: {meter.meter_number}")
        return meter

    async def get_meter(self, meter_id: int) -> Meter | None:
        """Получение счётчика с показаниями"""
        return await self.repository.get_with_readings(meter_id)

    async def update_meter(
        self,
        meter_id: int,
        **updates: Any,
    ) -> Meter | None:
        """Обновление счётчика"""
        updates.pop("meter_number", None)  # Запрещаем изменять номер
        return await self.repository.update(meter_id, **updates)

    async def delete_meter(self, meter_id: int) -> bool:
        """Удаление счётчика"""
        return await self.repository.delete(meter_id)

    async def add_reading(
        self,
        meter_id: int,
        reading_value: Decimal,
        reading_date: date | None = None,
        source: str = "manual",
    ) -> MeterReading:
        """Добавление показания"""
        if reading_date is None:
            reading_date = date.today()

        # Проверка существования счётчика
        meter = await self.repository.get(meter_id)
        if meter is None:
            raise NotFoundException("Счётчик", meter_id)

        # Проверка на дубликат
        existing = await self.repository.get_last_reading(meter_id)
        if existing and existing.reading_date == reading_date:
            raise ValidationException(
                f"Показание за {reading_date} уже существует",
                field="reading_date",
            )

        reading = await self.repository.add_reading(
            meter_id=meter_id,
            reading_value=reading_value,
            reading_date=reading_date,
            source=source,
        )

        logger.info(f"Добавлено показание для счётчика {meter_id}: {reading_value}")
        return reading

    async def process_meter_photo(
        self,
        meter_id: int,
        image_path: Path,
        reading_date: date | None = None,
    ) -> MeterReading:
        """
        Обработка фото счётчика через OCR.
        
        Процесс:
        1. OCR распознавание текста
        2. Парсинг значения
        3. Сохранение показания
        4. Логирование результата
        """
        import time
        start_time = time.time()

        # Проверка счётчика
        meter = await self.repository.get(meter_id)
        if meter is None:
            raise NotFoundException("Счётчик", meter_id)

        try:
            # OCR обработка
            ocr_result = await self.ocr_engine.process_image(str(image_path))
            
            # Парсинг значения
            parsed_value = self.ocr_engine.parse_reading(ocr_result)
            
            if parsed_value is None:
                raise MLException("Не удалось распознать показание счётчика")

            # Логирование
            processing_time = int((time.time() - start_time) * 1000)
            await self.cr_log_repository.log_processing(
                original_image=str(image_path),
                status="success",
                ocr_raw_text=ocr_result.get("text", ""),
                parsed_value=parsed_value,
                confidence=Decimal(str(ocr_result.get("confidence", 0))),
                processing_time_ms=processing_time,
            )

            # Создание показания
            reading = await self.add_reading(
                meter_id=meter_id,
                reading_value=parsed_value,
                reading_date=reading_date or date.today(),
                source="ocr",
            )

            logger.info(f"OCR обработка успешна: {parsed_value}")
            return reading

        except Exception as e:
            # Логирование ошибки
            await self.ocr_log_repository.log_processing(
                original_image=str(image_path),
                status="error",
                error_message=str(e),
            )
            logger.error(f"OCR обработка не удалась: {e}")
            raise MLException(f"Ошибка OCR: {e}")

    async def get_readings(
        self,
        meter_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[MeterReading]:
        """Получение показаний за период"""
        if start_date is None:
            start_date = date.today().replace(month=1, day=1)
        if end_date is None:
            end_date = date.today()

        return await self.repository.get_readings_period(
            meter_id=meter_id,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_consumption_stats(
        self,
        meter_id: int,
        months: int = 6,
    ) -> dict[str, Any]:
        """Получение статистики потребления"""
        meter = await self.repository.get(meter_id)
        if meter is None:
            raise NotFoundException("Счётчик", meter_id)

        stats = await self.repository.get_consumption_stats(meter_id, months)
        meter_type = await self.type_repository.get(meter.meter_type_id)

        return {
            "meter": {
                "id": meter.id,
                "number": meter.meter_number,
                "type": meter_type.name if meter_type else None,
                "unit": meter_type.unit if meter_type else None,
            },
            "consumption": stats,
        }

    async def get_meters_by_premise(
        self,
        premise_id: int,
    ) -> list[Meter]:
        """Получение счётчиков помещения"""
        return await self.repository.get_by_premise(premise_id)

    async def get_due_verification(self, days_ahead: int = 30) -> list[Meter]:
        """Получение счётчиков с предстоящей поверкой"""
        return await self.repository.get_due_verification(days_ahead)

    async def verify_reading(
        self,
        reading_id: int,
        verified_by: int,
    ) -> MeterReading | None:
        """Верификация показания"""
        from sqlalchemy import select
        
        result = await self.session.execute(
            select(MeterReading).where(MeterReading.id == reading_id)
        )
        reading = result.scalar_one_or_none()
        
        if reading is None:
            raise NotFoundException("Показание", reading_id)

        reading.is_verified = True
        reading.verified_by = verified_by
        reading.verified_at = datetime.now()

        await self.session.flush()
        await self.session.refresh(reading)

        logger.info(f"Показание {reading_id} верифицировано пользователем {verified_by}")
        return reading
