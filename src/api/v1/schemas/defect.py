"""
Pydantic схемы для модуля дефектов конструкций
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ============================================
# СХЕМЫ КЛАССОВ ДЕФЕКТОВ
# ============================================

class DefectClassBase(BaseModel):
    """Базовая схема класса дефекта"""
    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=20)
    yolo_class_id: Optional[int] = None
    description: Optional[str] = None
    severity_level: int = Field(default=1, ge=1, le=5)
    color: str = Field(default="#FF0000", pattern="^#[0-9A-Fa-f]{6}$")


class DefectClassCreate(DefectClassBase):
    """Создание класса дефекта"""
    pass


class DefectClassResponse(DefectClassBase):
    """Ответ с классом дефекта"""
    model_config = ConfigDict(from_attributes=True)
    id: int


# ============================================
# СХЕМЫ ОБСЛЕДОВАНИЙ
# ============================================

class InspectionCreate(BaseModel):
    """Создание обследования"""
    building_id: int
    premise_id: Optional[int] = None
    inspection_date: date = Field(default_factory=date.today)
    inspection_type: str = Field(
        default="routine",
        pattern="^(routine|emergency|planned|post_repair)$"
    )
    notes: Optional[str] = None


class InspectionUpdate(BaseModel):
    """Обновление обследования"""
    inspection_date: Optional[date] = None
    inspection_type: Optional[str] = None
    status: Optional[str] = Field(
        default=None,
        pattern="^(planned|in_progress|completed|cancelled)$"
    )
    notes: Optional[str] = None


class InspectionResponse(BaseModel):
    """Ответ с обследованием"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    inspection_number: str
    building_id: int
    premise_id: Optional[int] = None
    inspector_id: int
    inspection_date: date
    inspection_type: str
    status: str
    notes: Optional[str] = None
    created_at: datetime


# ============================================
# СХЕМЫ ДЕФЕКТОВ
# ============================================

class DefectResponse(BaseModel):
    """Ответ с детектированным дефектом"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    inspection_id: int
    photo_id: int
    defect_class_id: int
    confidence: Decimal
    bbox_x: Optional[int] = None
    bbox_y: Optional[int] = None
    bbox_width: Optional[int] = None
    bbox_height: Optional[int] = None
    severity: str
    status: str
    review_notes: Optional[str] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


class DefectReviewRequest(BaseModel):
    """Ревью дефекта инженером"""
    status: str = Field(
        ...,
        pattern="^(reviewed|fixed|ignored)$",
        description="Новый статус дефекта"
    )
    review_notes: Optional[str] = Field(default=None, max_length=1000)


# ============================================
# СХЕМЫ СТАТИСТИКИ
# ============================================

class DefectStatsResponse(BaseModel):
    """Статистика по дефектам"""
    total: int
    by_class: dict[str, int]
    by_severity: dict[str, int]
    by_status: dict[str, int]