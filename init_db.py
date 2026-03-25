"""Инициализация базы данных"""
import asyncio

# Импортируем ВСЕ модели чтобы они зарегистрировались в Base.metadata
from src.models.repair import RepairRequest, RepairPhoto, RepairComment, RepairType
from src.models.meter import Meter, MeterReading, MeterType, OCRProcessingLog
from src.models.defect import DefectClass, Inspection, DetectedDefect, InspectionPhoto
from src.models.report import Report, ReportTemplate, ReportEntity
from src.models.predictive import FailurePrediction, MaintenanceHistory
from src.models.user import User
from src.models.building import Building, Premise
from src.core.database import engine
from src.core.database import Base


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("Таблицы созданы:", list(Base.metadata.tables.keys()))

if __name__ == "__main__":
    asyncio.run(main())
