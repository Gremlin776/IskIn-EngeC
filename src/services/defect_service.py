"""
Сервис для детекции дефектов конструкций
"""

import uuid
from datetime import datetime, date
from typing import Any
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.defect import Inspection, DetectedDefect, DefectClass
from src.repositories.defect_repository import (
    DefectRepository,
    InspectionRepository,
    DefectClassRepository,
)
from src.core.exceptions import NotFoundException, MLException
from src.core.logging import get_logger
from src.ml.detection.yolo_engine import YOLOEngine

logger = get_logger(__name__)


class DefectService:
    """
    Сервис для управления обследованиями и детекцией дефектов.
    
    Бизнес-логика:
    - Создание обследований
    - YOLO детекция на фото
    - Классификация дефектов
    - Ревью дефектов
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = DefectRepository(session)
        self.inspection_repository = InspectionRepository(session)
        self.class_repository = DefectClassRepository(session)
        self.yolo_engine = YOLOEngine()

    def _generate_inspection_number(self) -> str:
        """Генерация номера обследования"""
        timestamp = datetime.now().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"INSP-{timestamp}-{unique_id}"

    async def create_inspection(
        self,
        building_id: int,
        inspector_id: int,
        inspection_date: date,
        premise_id: int | None = None,
        inspection_type: str = "routine",
        **kwargs,
    ) -> Inspection:
        """Создание обследования"""
        inspection = await self.inspection_repository.create(
            inspection_number=self._generate_inspection_number(),
            building_id=building_id,
            inspector_id=inspector_id,
            inspection_date=inspection_date,
            premise_id=premise_id,
            inspection_type=inspection_type,
            status="planned",
            **kwargs,
        )

        logger.info(f"Создано обследование: {inspection.inspection_number}")
        return inspection

    async def get_inspection(self, inspection_id: int) -> Inspection | None:
        """Получение обследования с фото и дефектами"""
        return await self.inspection_repository.get_with_relations(inspection_id)

    async def update_inspection(
        self,
        inspection_id: int,
        **updates: Any,
    ) -> Inspection | None:
        """Обновление обследования"""
        updates.pop("inspection_number", None)
        
        # Валидация статуса
        if "status" in updates:
            valid_statuses = {"planned", "in_progress", "completed", "cancelled"}
            if updates["status"] not in valid_statuses:
                raise ValueError(f"Неверный статус: {updates['status']}")

        return await self.inspection_repository.update(inspection_id, **updates)

    async def delete_inspection(self, inspection_id: int) -> bool:
        """Удаление обследования"""
        return await self.inspection_repository.delete(inspection_id)

    async def add_photo(
        self,
        inspection_id: int,
        file_path: Path,
        file_name: str,
        description: str | None = None,
        location_desc: str | None = None,
    ) -> Any:
        """Добавление фото к обследованию"""
        inspection = await self.inspection_repository.get(inspection_id)
        if inspection is None:
            raise NotFoundException("Обследование", inspection_id)

        return await self.inspection_repository.add_photo(
            inspection_id=inspection_id,
            file_path=str(file_path),
            file_name=file_name,
            description=description,
            location_desc=location_desc,
        )

    async def analyze_photo(
        self,
        inspection_id: int,
        photo_id: int,
        image_path: Path,
        min_confidence: float = 0.3,
    ) -> list[DetectedDefect]:
        """
        Анализ фото через YOLO для детекции дефектов.
        
        Процесс:
        1. YOLO детекция
        2. Фильтрация по confidence
        3. Сохранение дефектов
        """
        # Проверка обследования и фото
        inspection = await self.inspection_repository.get(inspection_id)
        if inspection is None:
            raise NotFoundException("Обследование", inspection_id)

        # YOLO детекция
        try:
            detection_results = await self.yolo_engine.detect(str(image_path))
        except Exception as e:
            logger.error(f"YOLO детекция не удалась: {e}")
            raise MLException(f"Ошибка детекции: {e}")

        detected_defects = []

        for detection in detection_results.get("detections", []):
            confidence = detection.get("confidence", 0)
            
            # Фильтрация по порогу уверенности
            if confidence < min_confidence:
                continue

            # Получение класса дефекта
            class_id = detection.get("class_id")
            defect_class = await self.class_repository.get(class_id)
            
            if defect_class is None:
                logger.warning(f"Класс дефекта {class_id} не найден")
                continue

            # Определение серьёзности на основе класса
            severity = self._calculate_severity(defect_class, confidence)

            # Создание дефекта
            defect = await self.repository.add_defect(
                inspection_id=inspection_id,
                photo_id=photo_id,
                defect_class_id=defect_class.id,
                confidence=confidence,
                bbox_x=detection.get("bbox", {}).get("x"),
                bbox_y=detection.get("bbox", {}).get("y"),
                bbox_width=detection.get("bbox", {}).get("width"),
                bbox_height=detection.get("bbox", {}).get("height"),
                severity=severity,
                status="detected",
            )
            detected_defects.append(defect)

        logger.info(f"Детектировано {len(detected_defects)} дефектов")
        return detected_defects

    def _calculate_severity(
        self,
        defect_class: DefectClass,
        confidence: float,
    ) -> str:
        """
        Расчёт серьёзности дефекта.
        
        Учитывает:
        - Базовый уровень серьёзности класса
        - Уверенность детекции
        """
        base_severity = defect_class.severity_level

        # Корректировка по уверенности
        if confidence > 0.8:
            base_severity = min(base_severity + 1, 5)
        elif confidence < 0.4:
            base_severity = max(base_severity - 1, 1)

        # Маппинг на строковое значение
        severity_map = {
            1: "low",
            2: "low",
            3: "medium",
            4: "high",
            5: "critical",
        }
        return severity_map.get(base_severity, "medium")

    async def review_defect(
        self,
        defect_id: int,
        status: str,
        reviewed_by: int,
        review_notes: str | None = None,
    ) -> DetectedDefect | None:
        """Ревью дефекта инженером"""
        valid_statuses = {"detected", "reviewed", "fixed", "ignored"}
        if status not in valid_statuses:
            raise ValueError(f"Неверный статус: {status}")

        return await self.repository.review_defect(
            defect_id=defect_id,
            status=status,
            reviewed_by=reviewed_by,
            review_notes=review_notes,
        )

    async def get_defects_by_inspection(
        self,
        inspection_id: int,
    ) -> list[DetectedDefect]:
        """Получение дефектов обследования"""
        return await self.repository.get_by_inspection(inspection_id)

    async def get_stats(self) -> dict[str, Any]:
        """Получение сводной статистики"""
        by_class = await self.repository.get_stats_by_class()
        by_severity = await self.repository.get_stats_by_severity()
        by_status = await self.repository.get_stats_by_status()
        total = await self.repository.count()

        return {
            "total": total,
            "by_class": by_class,
            "by_severity": by_severity,
            "by_status": by_status,
        }

    async def get_inspections_by_building(
        self,
        building_id: int,
    ) -> list[Inspection]:
        """Получение обследований здания"""
        return await self.inspection_repository.get_by_building(building_id)
