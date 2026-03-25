"""
Эндпоинты для модуля счётчиков и показаний
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pathlib import Path
import shutil
import uuid

from src.core.config import get_settings
from src.api.deps import CurrentUser, get_current_user, get_db
from src.services.meter_service import MeterService
from src.api.v1.schemas.meter import (
    MeterCreate, MeterUpdate, MeterResponse,
    MeterReadingCreate, MeterReadingResponse,
    MeterTypeCreate, MeterTypeResponse,
    MeterStatsResponse, OCRReadingResponse,
)

router = APIRouter()
settings = get_settings()


# ============================================
# Типы счётчиков
# ============================================

@router.get("/types", response_model=list[MeterTypeResponse])
async def get_meter_types(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получение типов счётчиков"""
    service = MeterService(db)
    return await service.get_types()


@router.post("/types", response_model=MeterTypeResponse,
             status_code=status.HTTP_201_CREATED)
async def create_meter_type(
    data: MeterTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Создание типа счётчика"""
    service = MeterService(db)
    return await service.create_type(**data.model_dump())


# ============================================
# Счётчики
# ============================================

@router.get("/", response_model=list[MeterResponse])
async def get_meters(
    premise_id: Optional[int] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получение списка счётчиков"""
    service = MeterService(db)
    if premise_id:
        return await service.get_meters_by_premise(premise_id)
    return await service.get_all(skip=skip, limit=limit)


@router.post("/", response_model=MeterResponse,
             status_code=status.HTTP_201_CREATED)
async def create_meter(
    data: MeterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Создание счётчика"""
    service = MeterService(db)
    return await service.create_meter(**data.model_dump())


@router.get("/{meter_id}", response_model=MeterResponse)
async def get_meter(
    meter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получение счётчика по ID"""
    service = MeterService(db)
    meter = await service.get(meter_id)
    if meter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Счётчик {meter_id} не найден"
        )
    return meter


@router.put("/{meter_id}", response_model=MeterResponse)
async def update_meter(
    meter_id: int,
    data: MeterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Обновление счётчика"""
    service = MeterService(db)
    meter = await service.update(meter_id, **data.model_dump(exclude_none=True))
    if meter is None:
        raise HTTPException(status_code=404, detail="Счётчик не найден")
    return meter


@router.delete("/{meter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meter(
    meter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Удаление счётчика"""
    service = MeterService(db)
    deleted = await service.delete(meter_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Счётчик не найден")


# ============================================
# Показания
# ============================================

@router.get("/{meter_id}/readings", response_model=list[MeterReadingResponse])
async def get_readings(
    meter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """История показаний счётчика"""
    service = MeterService(db)
    return await service.get_readings(meter_id)


@router.post("/{meter_id}/readings", response_model=MeterReadingResponse,
             status_code=status.HTTP_201_CREATED)
async def add_reading(
    meter_id: int,
    data: MeterReadingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Ручное добавление показания"""
    service = MeterService(db)
    return await service.add_reading(
        meter_id=meter_id,
        reading_value=data.reading_value,
        reading_date=data.reading_date,
        source="manual",
    )


@router.post("/{meter_id}/readings/ocr", response_model=MeterReadingResponse,
             status_code=status.HTTP_201_CREATED)
async def ocr_reading(
    meter_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """OCR обработка фото счётчика"""
    # Сохраняем фото
    upload_dir = Path(settings.upload_dir) / "meters" / str(meter_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = upload_dir / file_name

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    service = MeterService(db)
    return await service.process_ocr(
        meter_id=meter_id,
        image_path=file_path,
    )


# ============================================
# Статистика
# ============================================

@router.get("/stats/consumption")
async def get_consumption_stats(
    meter_id: int = Query(...),
    months: int = Query(default=6, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Статистика потребления по периодам"""
    service = MeterService(db)
    return await service.get_consumption_stats(meter_id, months)


@router.get("/stats/due-verification", response_model=list[MeterResponse])
async def get_due_verification(
    days_ahead: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Счётчики с предстоящей поверкой"""
    service = MeterService(db)
    return await service.get_due_verification(days_ahead)
