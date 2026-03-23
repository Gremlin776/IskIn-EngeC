"""
Репозиторий для детекции дефектов
"""

from datetime import date
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.defect import (
    DefectClass,
    Inspection,
    InspectionPhoto,
    DetectedDefect,
)
from src.repositories.base import BaseRepository


class DefectRepository(BaseRepository[DetectedDefect]):
    """Репозиторий для работы с дефектами"""

    model = DetectedDefect

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_with_relations(self, id: int) -> DetectedDefect | None:
        """Получить дефект с связями"""
        result = await self.session.execute(
            select(DetectedDefect)
            .options(
                selectinload(DetectedDefect.defect_class),
                selectinload(DetectedDefect.photo),
                selectinload(DetectedDefect.inspection),
            )
            .where(DetectedDefect.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_inspection(
        self,
        inspection_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[DetectedDefect]:
        """Получить дефекты по обследованию"""
        result = await self.session.execute(
            select(DetectedDefect)
            .options(selectinload(DetectedDefect.defect_class))
            .where(DetectedDefect.inspection_id == inspection_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[DetectedDefect]:
        """Получить дефекты по статусу"""
        result = await self.session.execute(
            select(DetectedDefect)
            .options(selectinload(DetectedDefect.defect_class))
            .where(DetectedDefect.status == status)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_severity(
        self,
        severity: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[DetectedDefect]:
        """Получить дефекты по серьёзности"""
        result = await self.session.execute(
            select(DetectedDefect)
            .options(selectinload(DetectedDefect.defect_class))
            .where(DetectedDefect.severity == severity)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_stats_by_class(self) -> dict[str, int]:
        """Получить статистику по классам дефектов"""
        result = await self.session.execute(
            select(DefectClass.code, func.count(DetectedDefect.id))
            .join(DetectedDefect, DefectClass.id == DetectedDefect.defect_class_id)
            .group_by(DefectClass.code)
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_stats_by_severity(self) -> dict[str, int]:
        """Получить статистику по серьёзности"""
        result = await self.session.execute(
            select(DetectedDefect.severity, func.count())
            .group_by(DetectedDefect.severity)
        )
        return {row[0]: row[1] for row in result.all()}

    async def get_stats_by_status(self) -> dict[str, int]:
        """Получить статистику по статусам"""
        result = await self.session.execute(
            select(DetectedDefect.status, func.count())
            .group_by(DetectedDefect.status)
        )
        return {row[0]: row[1] for row in result.all()}

    async def add_defect(
        self,
        inspection_id: int,
        photo_id: int,
        defect_class_id: int,
        confidence: float,
        **kwargs,
    ) -> DetectedDefect:
        """Добавить детектированный дефект"""
        defect = DetectedDefect(
            inspection_id=inspection_id,
            photo_id=photo_id,
            defect_class_id=defect_class_id,
            confidence=confidence,
            **kwargs,
        )
        self.session.add(defect)
        await self.session.flush()
        await self.session.refresh(defect)
        return defect

    async def review_defect(
        self,
        defect_id: int,
        status: str,
        reviewed_by: int,
        review_notes: str | None = None,
    ) -> DetectedDefect | None:
        """Ревью дефекта"""
        from datetime import datetime
        
        defect = await self.get(defect_id)
        if defect is None:
            return None
        
        defect.status = status
        defect.review_notes = review_notes
        defect.reviewed_by = reviewed_by
        defect.reviewed_at = datetime.now()
        
        await self.session.flush()
        await self.session.refresh(defect)
        return defect


class InspectionRepository(BaseRepository[Inspection]):
    """Репозиторий для обследований"""

    model = Inspection

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_with_relations(self, id: int) -> Inspection | None:
        """Получить обследование с фото и дефектами"""
        result = await self.session.execute(
            select(Inspection)
            .options(
                selectinload(Inspection.photos),
                selectinload(Inspection.defects).selectinload(DetectedDefect.defect_class),
                selectinload(Inspection.building),
                selectinload(Inspection.premise),
            )
            .where(Inspection.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_building(
        self,
        building_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Inspection]:
        """Получить обследования по зданию"""
        result = await self.session.execute(
            select(Inspection)
            .where(Inspection.building_id == building_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Inspection]:
        """Получить обследования по статусу"""
        result = await self.session.execute(
            select(Inspection)
            .where(Inspection.status == status)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_photo(
        self,
        inspection_id: int,
        file_path: str,
        file_name: str,
        **kwargs,
    ) -> InspectionPhoto:
        """Добавить фото к обследованию"""
        photo = InspectionPhoto(
            inspection_id=inspection_id,
            file_path=file_path,
            file_name=file_name,
            **kwargs,
        )
        self.session.add(photo)
        await self.session.flush()
        await self.session.refresh(photo)
        return photo


class DefectClassRepository(BaseRepository[DefectClass]):
    """Репозиторий для классов дефектов"""

    model = DefectClass

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_code(self, code: str) -> DefectClass | None:
        """Получить класс по коду"""
        result = await self.session.execute(
            select(DefectClass).where(DefectClass.code == code)
        )
        return result.scalar_one_or_none()
