"""
Эндпоинты для модуля детекции дефектов конструкций
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pathlib import Path
import shutil
import uuid

from src.core.config import get_settings
from src.api.deps import CurrentUser, get_current_user, get_db
from src.services.defect_service import DefectService
from src.api.v1.schemas.defect import (
    InspectionCreate, InspectionUpdate, InspectionResponse,
    DefectResponse, DefectReviewRequest, DefectStatsResponse,
    DefectClassCreate, DefectClassResponse,
)

router = APIRouter()
settings = get_settings()


# ============================================
# Классы дефектов
# ============================================

@router.get("/classes", response_model=list[DefectClassResponse])
async def get_defect_classes(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получение классов дефектов"""
    service = DefectService(db)
    return await service.get_defect_classes()


@router.post("/classes", response_model=DefectClassResponse,
             status_code=status.HTTP_201_CREATED)
async def create_defect_class(
    data: DefectClassCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Создание класса дефекта"""
    service = DefectService(db)
    return await service.create_defect_class(**data.model_dump())


# ============================================
# Обследования
# ============================================

@router.get("/inspections", response_model=list[InspectionResponse])
async def get_inspections(
    building_id: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получение списка обследований"""
    service = DefectService(db)
    if building_id:
        return await service.get_inspections_by_building(building_id)
    return await service.get_all_inspections(skip=skip, limit=limit)


@router.post("/inspections", response_model=InspectionResponse,
             status_code=status.HTTP_201_CREATED)
async def create_inspection(
    data: InspectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Создание обследования"""
    service = DefectService(db)
    return await service.create_inspection(
        inspector_id=current_user.id,
        **data.model_dump()
    )


@router.get("/inspections/{inspection_id}", response_model=InspectionResponse)
async def get_inspection(
    inspection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получение обследования по ID"""
    service = DefectService(db)
    inspection = await service.get_inspection(inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail="Обследование не найдено")
    return inspection


@router.put("/inspections/{inspection_id}", response_model=InspectionResponse)
async def update_inspection(
    inspection_id: int,
    data: InspectionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Обновление обследования"""
    service = DefectService(db)
    inspection = await service.update_inspection(
        inspection_id, **data.model_dump(exclude_none=True)
    )
    if inspection is None:
        raise HTTPException(status_code=404, detail="Обследование не найдено")
    return inspection


# ============================================
# Фото и анализ YOLO
# ============================================

@router.post("/inspections/{inspection_id}/photos",
             status_code=status.HTTP_201_CREATED)
async def upload_inspection_photo(
    inspection_id: int,
    file: UploadFile = File(...),
    description: Optional[str] = None,
    location_desc: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Загрузка фото обследования"""
    upload_dir = Path(settings.upload_dir) / "inspections" / str(inspection_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = upload_dir / file_name

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    service = DefectService(db)
    return await service.add_photo(
        inspection_id=inspection_id,
        file_path=str(file_path),
        file_name=file_name,
        description=description,
        location_desc=location_desc,
    )


@router.post("/inspections/{inspection_id}/analyze")
async def analyze_inspection(
    inspection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Запуск YOLO анализа всех фото обследования"""
    service = DefectService(db)
    defects = await service.analyze_inspection(inspection_id)
    return {
        "inspection_id": inspection_id,
        "detected": len(defects),
        "defects": defects,
    }


@router.get("/inspections/{inspection_id}/defects",
            response_model=list[DefectResponse])
async def get_inspection_defects(
    inspection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Дефекты обследования"""
    service = DefectService(db)
    return await service.get_defects_by_inspection(inspection_id)


# ============================================
# Управление дефектами
# ============================================

@router.put("/{defect_id}/review", response_model=DefectResponse)
async def review_defect(
    defect_id: int,
    data: DefectReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Ревью дефекта инженером"""
    service = DefectService(db)
    defect = await service.review_defect(
        defect_id=defect_id,
        status=data.status,
        reviewed_by=current_user.id,
        review_notes=data.review_notes,
    )
    if defect is None:
        raise HTTPException(status_code=404, detail="Дефект не найден")
    return defect


# ============================================
# Статистика
# ============================================

@router.get("/stats/summary", response_model=DefectStatsResponse)
async def get_defect_stats(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Сводная статистика по дефектам"""
    service = DefectService(db)
    return await service.get_stats()
