# -*- coding: utf-8 -*-
"""
Эндпоинты для модуля ремонтных работ
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pathlib import Path
import shutil
import uuid

from src.core.config import get_settings
from src.api.deps import CurrentUser, get_current_user, get_db
from src.services.repair_service import RepairService
from src.api.v1.schemas.repair import (
    RepairRequestCreate, RepairRequestUpdate, RepairRequestResponse,
    RepairRequestStatusUpdate, RepairPhotoResponse, RepairCommentCreate,
    RepairCommentResponse, RepairStatsResponse, RepairTypeCreate, RepairTypeResponse,
)

router = APIRouter()
settings = get_settings()


# ============================================
# Типы ремонта
# ============================================

@router.get("/types", response_model=list[RepairTypeResponse])
async def get_repair_types(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получение списка типов ремонта"""
    service = RepairService(db)
    return await service.get_types()


@router.post("/types", response_model=RepairTypeResponse,
             status_code=status.HTTP_201_CREATED)
async def create_repair_type(
    data: RepairTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Создание типа ремонта"""
    service = RepairService(db)
    return await service.create_type(**data.model_dump())


# ============================================
# Заявки на ремонт
# ============================================

@router.get("/requests", response_model=list[RepairRequestResponse])
async def get_repair_requests(
    status: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    premise_id: Optional[int] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получение списка заявок с фильтрами"""
    service = RepairService(db)
    if status:
        return await service.get_requests_by_status(status, skip, limit)
    if premise_id:
        return await service.get_requests_by_premise(premise_id, skip, limit)
    return await service.get_all(skip=skip, limit=limit)


@router.post("/requests", response_model=RepairRequestResponse,
             status_code=status.HTTP_201_CREATED)
async def create_repair_request(
    data: RepairRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Создание заявки на ремонт"""
    service = RepairService(db)
    return await service.create_request(
        user_id=current_user.id,
        **data.model_dump()
    )


@router.get("/requests/{request_id}", response_model=RepairRequestResponse)
async def get_repair_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получение заявки по ID"""
    service = RepairService(db)
    request = await service.get_request(request_id)
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Заявка {request_id} не найдена"
        )
    return request


@router.put("/requests/{request_id}", response_model=RepairRequestResponse)
async def update_repair_request(
    request_id: int,
    data: RepairRequestUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Обновление заявки"""
    service = RepairService(db)
    request = await service.update_request(
        request_id, **data.model_dump(exclude_none=True)
    )
    if request is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return request


@router.patch("/requests/{request_id}/status", response_model=RepairRequestResponse)
async def update_repair_status(
    request_id: int,
    data: RepairRequestStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Изменение статуса заявки"""
    service = RepairService(db)
    request = await service.update_request(request_id, status=data.status)
    if request is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return request


@router.delete("/requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repair_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Удаление заявки"""
    service = RepairService(db)
    deleted = await service.delete_request(request_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Заявка не найдена")


# ============================================
# Фотографии
# ============================================

@router.post("/requests/{request_id}/photos",
             response_model=RepairPhotoResponse,
             status_code=status.HTTP_201_CREATED)
async def upload_repair_photo(
    request_id: int,
    file: UploadFile = File(...),
    description: Optional[str] = None,
    is_main: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Загрузка фото к заявке"""
    # Сохраняем файл
    upload_dir = Path(settings.upload_dir) / "repair" / str(request_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = upload_dir / file_name

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    service = RepairService(db)
    return await service.add_photo(
        request_id=request_id,
        file_path=file_path,
        file_name=file_name,
        description=description,
        is_main=is_main,
    )


# ============================================
# Комментарии
# ============================================

@router.post("/requests/{request_id}/comments",
             response_model=RepairCommentResponse,
             status_code=status.HTTP_201_CREATED)
async def add_comment(
    request_id: int,
    data: RepairCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Добавление комментария к заявке"""
    service = RepairService(db)
    return await service.add_comment(
        request_id=request_id,
        user_id=current_user.id,
        comment_text=data.comment_text,
    )


# ============================================
# Статистика
# ============================================

@router.get("/stats/summary", response_model=RepairStatsResponse)
async def get_repair_stats(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Сводная статистика по ремонтам"""
    service = RepairService(db)
    return await service.get_stats()
