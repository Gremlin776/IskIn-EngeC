"""
Pydantic схемы для модуля отчётов
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ============================================
# СХЕМЫ ШАБЛОНОВ
# ============================================

class ReportTemplateBase(BaseModel):
    """Базовая схема шаблона отчёта"""
    name: str = Field(..., min_length=2, max_length=100)
    code: str = Field(..., min_length=2, max_length=20)
    description: Optional[str] = None
    template_type: str = Field(
        ...,
        pattern="^(repair|inspection|meter|general)$"
    )


class ReportTemplateCreate(ReportTemplateBase):
    """Создание шаблона"""
    pass


class ReportTemplateResponse(ReportTemplateBase):
    """Ответ с шаблоном"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool
    created_at: datetime


# ============================================
# СХЕМЫ ОТЧЁТОВ
# ============================================

class ReportCreate(BaseModel):
    """Создание отчёта вручную"""
    template_id: Optional[int] = None
    title: str = Field(..., min_length=5, max_length=200)
    report_type: str = Field(..., max_length=50)
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    content: Optional[str] = None


class ReportResponse(BaseModel):
    """Ответ с отчётом"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_number: str
    template_id: Optional[int] = None
    user_id: int
    title: str
    report_type: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    content: Optional[str] = None
    llm_model_used: Optional[str] = None
    file_path: Optional[str] = None
    status: str
    created_at: datetime


# ============================================
# СХЕМЫ ГЕНЕРАЦИИ ОТЧЁТОВ
# ============================================

class ReportGenerateRequest(BaseModel):
    """Запрос на генерацию отчёта через LLM"""
    report_type: str = Field(
        ...,
        pattern="^(repair|inspection|monthly|custom)$",
        description="Тип отчёта"
    )
    entity_id: Optional[int] = Field(
        default=None,
        description="ID объекта (заявки или обследования)"
    )
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    custom_prompt: Optional[str] = Field(
        default=None,
        description="Дополнительные инструкции для LLM"
    )