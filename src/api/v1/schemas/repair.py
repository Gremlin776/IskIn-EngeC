"""
Pydantic схемы для модуля ремонтных работ
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ============================================
# СХЕМЫ ТИПОВ РЕМОНТА
# ============================================

class RepairTypeBase(BaseModel):
    """Базовая схема типа ремонта"""
    name: str = Field(..., min_length=2, max_length=100, description="Название типа")
    code: str = Field(..., min_length=2, max_length=20, description="Код типа")
    description: Optional[str] = None
    priority: int = Field(default=1, ge=1, le=10)


class RepairTypeCreate(RepairTypeBase):
    """Создание типа ремонта"""
    pass


class RepairTypeResponse(RepairTypeBase):
    """Ответ с типом ремонта"""
    model_config = ConfigDict(from_attributes=True)
    id: int


# ============================================
# СХЕМЫ ЗАЯВОК НА РЕМОНТ
# ============================================

class RepairRequestCreate(BaseModel):
    """Создание заявки на ремонт"""
    premise_id: int = Field(..., description="ID помещения")
    repair_type_id: Optional[int] = None
    title: str = Field(..., min_length=5, max_length=200, description="Заголовок")
    description: str = Field(..., min_length=10, description="Описание работ")
    priority: str = Field(
        default="medium",
        pattern="^(low|medium|high|critical)$",
        description="Приоритет"
    )
    scheduled_date: Optional[date] = None
    cost: Optional[Decimal] = Field(default=None, ge=0)
    notes: Optional[str] = None


class RepairRequestUpdate(BaseModel):
    """Обновление заявки на ремонт — все поля опциональны"""
    repair_type_id: Optional[int] = None
    title: Optional[str] = Field(default=None, min_length=5, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10)
    priority: Optional[str] = Field(
        default=None,
        pattern="^(low|medium|high|critical)$"
    )
    scheduled_date: Optional[date] = None
    completed_date: Optional[date] = None
    cost: Optional[Decimal] = Field(default=None, ge=0)
    notes: Optional[str] = None


class RepairRequestStatusUpdate(BaseModel):
    """Обновление статуса заявки"""
    status: str = Field(
        ...,
        pattern="^(new|in_progress|completed|cancelled)$",
        description="Новый статус"
    )


class RepairRequestResponse(BaseModel):
    """Ответ с заявкой на ремонт"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_number: str
    premise_id: int
    user_id: int
    repair_type_id: Optional[int] = None
    title: str
    description: str
    status: str
    priority: str
    scheduled_date: Optional[date] = None
    completed_date: Optional[date] = None
    cost: Optional[Decimal] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============================================
# СХЕМЫ ФОТОГРАФИЙ
# ============================================

class RepairPhotoCreate(BaseModel):
    """Добавление фото к заявке"""
    description: Optional[str] = Field(default=None, max_length=255)
    is_main: bool = False


class RepairPhotoResponse(BaseModel):
    """Ответ с фото"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    repair_request_id: int
    file_path: str
    file_name: str
    file_size: Optional[int] = None
    description: Optional[str] = None
    is_main: bool
    uploaded_at: datetime


# ============================================
# СХЕМЫ КОММЕНТАРИЕВ
# ============================================

class RepairCommentCreate(BaseModel):
    """Добавление комментария"""
    comment_text: str = Field(..., min_length=1, max_length=2000)


class RepairCommentResponse(BaseModel):
    """Ответ с комментарием"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    repair_request_id: int
    user_id: int
    comment_text: str
    created_at: datetime


# ============================================
# СХЕМЫ СТАТИСТИКИ
# ============================================

class RepairStatsResponse(BaseModel):
    """Сводная статистика ремонтов"""
    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]