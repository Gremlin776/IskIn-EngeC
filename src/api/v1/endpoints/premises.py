"""
Эндпоинты для управления помещениями
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from src.api.deps import CurrentUser, get_current_user, get_db
from src.models.repair import Premise

router = APIRouter()


# ============================================
# Локальные схемы
# ============================================

class PremiseCreate(BaseModel):
    building_id: int
    floor: int = Field(..., ge=-10, le=200)
    room_number: str = Field(..., min_length=1, max_length=20)
    room_name: Optional[str] = Field(default=None, max_length=100)
    room_type: Optional[str] = Field(
        default=None,
        pattern="^(office|technical|storage|common|other)$"
    )
    area: Optional[float] = Field(default=None, ge=0)


class PremiseUpdate(BaseModel):
    room_name: Optional[str] = None
    room_type: Optional[str] = None
    area: Optional[float] = None
    is_active: Optional[bool] = None


class PremiseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    building_id: int
    floor: int
    room_number: str
    room_name: Optional[str] = None
    room_type: Optional[str] = None
    area: Optional[float] = None
    is_active: bool
    created_at: datetime


# ============================================
# Эндпоинты
# ============================================

@router.get("/", response_model=list[PremiseResponse])
async def get_premises(
    building_id: Optional[int] = Query(default=None),
    floor: Optional[int] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получение списка помещений с фильтрами"""
    query = select(Premise)
    if building_id is not None:
        query = query.where(Premise.building_id == building_id)
    if floor is not None:
        query = query.where(Premise.floor == floor)
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=PremiseResponse, status_code=status.HTTP_201_CREATED)
async def create_premise(
    data: PremiseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Создание помещения"""
    premise = Premise(**data.model_dump())
    db.add(premise)
    await db.commit()
    await db.refresh(premise)
    return premise


@router.get("/{premise_id}", response_model=PremiseResponse)
async def get_premise(
    premise_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получение помещения по ID"""
    result = await db.execute(
        select(Premise).where(Premise.id == premise_id)
    )
    premise = result.scalar_one_or_none()
    if premise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Помещение {premise_id} не найдено"
        )
    return premise


@router.put("/{premise_id}", response_model=PremiseResponse)
async def update_premise(
    premise_id: int,
    data: PremiseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Обновление помещения"""
    result = await db.execute(
        select(Premise).where(Premise.id == premise_id)
    )
    premise = result.scalar_one_or_none()
    if premise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Помещение {premise_id} не найдено"
        )

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(premise, field, value)

    await db.commit()
    await db.refresh(premise)
    return premise


@router.delete("/{premise_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_premise(
    premise_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Удаление помещения (мягкое)"""
    result = await db.execute(
        select(Premise).where(Premise.id == premise_id)
    )
    premise = result.scalar_one_or_none()
    if premise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Помещение {premise_id} не найдено"
        )
    premise.is_active = False
    await db.commit()
