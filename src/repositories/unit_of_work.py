# -*- coding: utf-8 -*-
"""
Unit of Work паттерн для управления транзакциями
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.repair_repository import RepairRepository, RepairTypeRepository
from src.repositories.meter_repository import (
    MeterRepository,
    MeterTypeRepository,
    OCRProcessingLogRepository,
)
from src.repositories.defect_repository import (
    DefectRepository,
    InspectionRepository,
    DefectClassRepository,
)


class UnitOfWork:
    """
    Unit of Work — координация репозиториев в рамках транзакции.
    
    Использование:
        async with UnitOfWork(session) as uow:
            repair = await uow.repairs.create(...)
            await uow.repairs.add_photo(...)
            # commit вызывается автоматически
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._repairs: RepairRepository | None = None
        self._repair_types: RepairTypeRepository | None = None
        self._meters: MeterRepository | None = None
        self._meter_types: MeterTypeRepository | None = None
        self._ocr_logs: OCRProcessingLogRepository | None = None
        self._defects: DefectRepository | None = None
        self._inspections: InspectionRepository | None = None
        self._defect_classes: DefectClassRepository | None = None

    @property
    def repairs(self) -> RepairRepository:
        """Репозиторий заявок на ремонт"""
        if self._repairs is None:
            self._repairs = RepairRepository(self.session)
        return self._repairs

    @property
    def repair_types(self) -> RepairTypeRepository:
        """Репозиторий типов ремонтов"""
        if self._repair_types is None:
            self._repair_types = RepairTypeRepository(self.session)
        return self._repair_types

    @property
    def meters(self) -> MeterRepository:
        """Репозиторий счётчиков"""
        if self._meters is None:
            self._meters = MeterRepository(self.session)
        return self._meters

    @property
    def meter_types(self) -> MeterTypeRepository:
        """Репозиторий типов счётчиков"""
        if self._meter_types is None:
            self._meter_types = MeterTypeRepository(self.session)
        return self._meter_types

    @property
    def ocr_logs(self) -> OCRProcessingLogRepository:
        """Репозиторий логов OCR"""
        if self._ocr_logs is None:
            self._ocr_logs = OCRProcessingLogRepository(self.session)
        return self._ocr_logs

    @property
    def defects(self) -> DefectRepository:
        """Репозиторий дефектов"""
        if self._defects is None:
            self._defects = DefectRepository(self.session)
        return self._defects

    @property
    def inspections(self) -> InspectionRepository:
        """Репозиторий обследований"""
        if self._inspections is None:
            self._inspections = InspectionRepository(self.session)
        return self._inspections

    @property
    def defect_classes(self) -> DefectClassRepository:
        """Репозиторий классов дефектов"""
        if self._defect_classes is None:
            self._defect_classes = DefectClassRepository(self.session)
        return self._defect_classes

    async def commit(self) -> None:
        """Закоммитить транзакцию"""
        await self.session.commit()

    async def rollback(self) -> None:
        """Откатить транзакцию"""
        await self.session.rollback()

    async def __aenter__(self):
        """Вход в контекст"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекста"""
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
