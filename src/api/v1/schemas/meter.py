"""
Pydantic схемы для модуля счётчиков
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ============================================
# СХЕМЫ ТИПОВ СЧЁТЧИКОВ
# ============================================

class MeterTypeBase(BaseModel):
    """Базовая схема типа счётчика"""
    name: str = Field(..., min_length=2, max_length=50)
    code: str = Field(..., min_length=2, max_length=20)
    unit: str = Field(..., max_length=20, description="Единица измерения")
    icon: Optional[str] = None


class MeterTypeCreate(MeterTypeBase):
    """Создание типа счётчика"""
    pass


class MeterTypeResponse(MeterTypeBase):
    """Ответ с типом счётчика"""
    model_config = ConfigDict(from_attributes=True)
    id: int


# ============================================
# СХЕМЫ СЧЁТЧИКОВ
# ============================================

class MeterCreate(BaseModel):
    """Создание счётчика"""
    meter_number: str = Field(..., min_length=3, max_length=50)
    premise_id: int
    meter_type_id: int
    manufacturer: Optional[str] = Field(default=None, max_length=100)
    model: Optional[str] = Field(default=None, max_length=100)
    serial_number: Optional[str] = Field(default=None, max_length=100)
    install_date: Optional[date] = None
    verification_date: Optional[date] = None
    next_verification: Optional[date] = None


class MeterUpdate(BaseModel):
    """Обновление счётчика — все поля опциональны"""
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    install_date: Optional[date] = None
    verification_date: Optional[date] = None
    next_verification: Optional[date] = None
    is_active: Optional[bool] = None


class MeterResponse(BaseModel):
    """Ответ со счётчиком"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    meter_number: str
    premise_id: int
    meter_type_id: int
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    install_date: Optional[date] = None
    verification_date: Optional[date] = None
    next_verification: Optional[date] = None
    is_active: bool
    created_at: datetime


# ============================================
# СХЕМЫ ПОКАЗАНИЙ
# ============================================

class MeterReadingCreate(BaseModel):
    """Ручное добавление показания"""
    reading_value: Decimal = Field(..., ge=0, decimal_places=4)
    reading_date: date = Field(default_factory=date.today)
    notes: Optional[str] = None


class MeterReadingResponse(BaseModel):
    """Ответ с показанием"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    meter_id: int
    reading_value: Decimal
    reading_date: date
    photo_path: Optional[str] = None
    ocr_confidence: Optional[Decimal] = None
    is_verified: bool
    source: str
    created_at: datetime


class OCRReadingResponse(BaseModel):
    """Ответ после OCR обработки фото"""
    reading: MeterReadingResponse
    ocr_confidence: float
    raw_text: Optional[str] = None
    processing_time_ms: int


# ============================================
# СХЕМЫ СТАТИСТИКИ
# ============================================

class ConsumptionPeriod(BaseModel):
    """Потребление за период"""
    period: str
    consumption: Decimal
    unit: str


class MeterStatsResponse(BaseModel):
    """Статистика потребления счётчика"""
    meter: dict
    consumption: list[ConsumptionPeriod]