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
    # Common
    "ResponseModel",
    "PaginatedResponse",
    "HealthResponse",
    # Repair
    "RepairRequestCreate",
    "RepairRequestUpdate",
    "RepairRequestResponse",
    "RepairPhotoCreate",
    "RepairCommentCreate",
    "RepairStatsResponse",
    # Meter
    "MeterCreate",
    "MeterUpdate",
    "MeterResponse",
    "MeterReadingCreate",
    "MeterReadingResponse",
    "MeterStatsResponse",
    # Defect
    "InspectionCreate",
    "InspectionUpdate",
    "InspectionResponse",
    "DefectResponse",
    "DefectReviewRequest",
    "DefectStatsResponse",
    # Report
    "ReportCreate",
    "ReportResponse",
    "ReportGenerateRequest",
    # Predictive
    "PredictionResponse",
    "RiskRatingResponse",
    "PredictiveAnalyzeRequest",
]
