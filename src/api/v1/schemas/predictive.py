"""
Pydantic схемы для модуля предиктивной аналитики
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class PredictionResponse(BaseModel):
    """Ответ с прогнозом поломки"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    premise_id: Optional[int] = None
    meter_id: Optional[int] = None
    equipment_type: Optional[str] = None
    prediction_date: date
    failure_probability: Decimal
    predicted_failure_date: Optional[date] = None
    confidence_level: Optional[str] = None
    risk_factors: Optional[str] = None
    recommendations: Optional[str] = None
    model_version: Optional[str] = None
    created_at: datetime


class PredictiveAnalyzeRequest(BaseModel):
    """Запрос на анализ объекта"""
    force_recalculate: bool = Field(
        default=False,
        description="Пересчитать даже если прогноз уже есть"
    )


class RiskRatingItem(BaseModel):
    """Элемент рейтинга рисков"""
    building_id: Optional[int] = None
    meter_id: Optional[int] = None
    name: Optional[str] = None
    number: Optional[str] = None
    risk_level: Optional[str] = None
    failure_probability: Optional[Decimal] = None
    predicted_date: Optional[date] = None
    critical_defects: Optional[int] = None


class RiskRatingResponse(BaseModel):
    """Рейтинг рисков"""
    items: list[RiskRatingItem]
    total: int


class ModelInfoResponse(BaseModel):
    """Информация о ML модели"""
    model_version: str
    last_trained: Optional[datetime] = None
    training_samples: Optional[int] = None
    accuracy: Optional[float] = None
    features: list[str] = []


class RetrainResponse(BaseModel):
    """Результат переобучения"""
    success: bool
    message: str
    details: Optional[dict[str, Any]] = None