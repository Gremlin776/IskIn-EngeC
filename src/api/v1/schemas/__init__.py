# -*- coding: utf-8 -*-
"""
Pydantic схемы API v1
"""

from src.api.v1.schemas.common import (
    ResponseModel,
    PaginatedResponse,
    HealthResponse,
)
from src.api.v1.schemas.repair import (
    RepairRequestCreate,
    RepairRequestUpdate,
    RepairRequestResponse,
    RepairPhotoCreate,
    RepairCommentCreate,
    RepairStatsResponse,
)
from src.api.v1.schemas.meter import (
    MeterCreate,
    MeterUpdate,
    MeterResponse,
    MeterReadingCreate,
    MeterReadingResponse,
    MeterStatsResponse,
)
from src.api.v1.schemas.defect import (
    InspectionCreate,
    InspectionUpdate,
    InspectionResponse,
    DefectResponse,
    DefectReviewRequest,
    DefectStatsResponse,
)
from src.api.v1.schemas.report import (
    ReportCreate,
    ReportResponse,
    ReportGenerateRequest,
)
from src.api.v1.schemas.predictive import (
    PredictionResponse,
    RiskRatingResponse,
    PredictiveAnalyzeRequest,
)

__all__ = [
    # Общие схемы
    "ResponseModel",
    "PaginatedResponse",
    "HealthResponse",
    # Схемы заявок на ремонт
    "RepairRequestCreate",
    "RepairRequestUpdate",
    "RepairRequestResponse",
    "RepairPhotoCreate",
    "RepairCommentCreate",
    "RepairStatsResponse",
    # Схемы учёта показаний
    "MeterCreate",
    "MeterUpdate",
    "MeterResponse",
    "MeterReadingCreate",
    "MeterReadingResponse",
    "MeterStatsResponse",
    # Схемы инспекций и дефектов
    "InspectionCreate",
    "InspectionUpdate",
    "InspectionResponse",
    "DefectResponse",
    "DefectReviewRequest",
    "DefectStatsResponse",
    # Схемы отчётности
    "ReportCreate",
    "ReportResponse",
    "ReportGenerateRequest",
    # Схемы предиктивной аналитики
    "PredictionResponse",
    "RiskRatingResponse",
    "PredictiveAnalyzeRequest",
]
