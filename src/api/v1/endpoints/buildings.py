# -*- coding: utf-8 -*-
"""
Эндпоинты для управления зданиями
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from src.core.exceptions import NotFoundException
from src.api.deps import CurrentUser, get_current_user, get_db
from src.models.building import Building, Premise

router = APIRouter()


# ============================================
# Локальные схемы
# ============================================

class BuildingCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    address: str = Field(..., min_length=5, max_length=255)
    building_type: Optional[str] = None
    year_built: Optional[int] = Field(default=None, ge=1800, le=2100)
    floors: Optional[int] = Field(default=None, ge=1, le=200)
    total_area: Optional[float] = Field(default=None, ge=0)


class BuildingUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    address: Optional[str] = Field(default=None, min_length=5, max_length=255)
    building_type: Optional[str] = None
    year_built: Optional[int] = None
    floors: Optional[int] = None
    total_area: Optional[float] = None
    is_active: Optional[bool] = None


class BuildingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str
    building_type: Optional[str] = None
    year_built: Optional[int] = None
    floors: Optional[int] = None
    total_area: Optional[float] = None
    is_active: bool
    created_at: datetime


# ============================================
# Эндпоинты
# ============================================

@router.get("/", response_model=list[BuildingResponse])
async def get_buildings(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    is_active: Optional[bool] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получение списка зданий"""
    query = select(Building)
    if is_active is not None:
        query = query.where(Building.is_active == is_active)
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=BuildingResponse, status_code=status.HTTP_201_CREATED)
async def create_building(
    data: BuildingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Создание нового здания"""
    building = Building(**data.model_dump())
    db.add(building)
    await db.commit()
    await db.refresh(building)
    return building


@router.get("/{building_id}", response_model=BuildingResponse)
async def get_building(
    building_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получение здания по ID"""
    result = await db.execute(
        select(Building).where(Building.id == building_id)
    )
    building = result.scalar_one_or_none()
    if building is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Здание {building_id} не найдено"
        )
    return building


@router.put("/{building_id}", response_model=BuildingResponse)
async def update_building(
    building_id: int,
    data: BuildingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Обновление здания"""
    result = await db.execute(
        select(Building).where(Building.id == building_id)
    )
    building = result.scalar_one_or_none()
    if building is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Здание {building_id} не найдено"
        )

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(building, field, value)

    await db.commit()
    await db.refresh(building)
    return building


@router.delete("/{building_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_building(
    building_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Удаление здания (мягкое — is_active=False)"""
    result = await db.execute(
        select(Building).where(Building.id == building_id)
    )
    building = result.scalar_one_or_none()
    if building is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Здание {building_id} не найдено"
        )
    building.is_active = False
    await db.commit()


@router.get("/{building_id}/stats")
async def get_building_stats(
    building_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Статистика по зданию"""
    # Количество помещений
    premises_count = await db.execute(
        select(func.count()).select_from(Premise)
        .where(Premise.building_id == building_id)
    )

    return {
        "building_id": building_id,
        "premises_count": premises_count.scalar() or 0,
    }
