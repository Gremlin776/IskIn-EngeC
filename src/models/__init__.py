"""
SQLAlchemy ORM модели
"""

from datetime import datetime, date

from src.models.base import BaseModel, TimestampMixin
from src.models.user import User
from src.models.building import Building, Premise
from src.models.repair import (
    RepairType,
    RepairRequest,
    RepairPhoto,
    RepairComment,
)
from src.models.meter import (
    MeterType,
    Meter,
    MeterReading,
    OCRProcessingLog,
)
from src.models.defect import (
    DefectClass,
    Inspection,
    InspectionPhoto,
    DetectedDefect,
)
from src.models.report import (
    ReportTemplate,
    Report,
    ReportEntity,
)
from src.models.predictive import (
    FailurePrediction,
    MaintenanceHistory,
)

__all__ = [
    "BaseModel",
    "TimestampMixin",
    "User",
    "Building",
    "Premise",
    "RepairType",
    "RepairRequest",
    "RepairPhoto",
    "RepairComment",
    "MeterType",
    "Meter",
    "MeterReading",
    "OCRProcessingLog",
    "DefectClass",
    "Inspection",
    "InspectionPhoto",
    "DetectedDefect",
    "ReportTemplate",
    "Report",
    "ReportEntity",
    "FailurePrediction",
    "MaintenanceHistory",
]
