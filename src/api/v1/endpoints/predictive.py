# -*- coding: utf-8 -*-
"""
Эндпоинты для модуля предиктивной аналитики
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import CurrentUser, get_current_user, get_db
from src.services.predictive_service import PredictiveService
from src.api.v1.schemas.predictive import (
    PredictionResponse, RiskRatingResponse,
    PredictiveAnalyzeRequest, ModelInfoResponse,
    RetrainResponse,
)

router = APIRouter()


# ============================================
# Прогнозы
# ============================================

@router.get("/failures", response_model=list[PredictionResponse])
async def get_predictions(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Список всех прогнозов поломок"""
    service = PredictiveService(db)
    return await service.get_all_predictions()


@router.get("/failures/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(
    prediction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Детали прогноза"""
    service = PredictiveService(db)
    prediction = await service.get_prediction(prediction_id)
    if prediction is None:
        raise HTTPException(status_code=404, detail="Прогноз не найден")
    return prediction


# ============================================
# Анализ объектов
# ============================================

@router.post("/analyze/building/{building_id}")
async def analyze_building(
    building_id: int,
    data: PredictiveAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Анализ рисков здания"""
    service = PredictiveService(db)
    return await service.analyze_building(building_id)


@router.post("/analyze/meter/{meter_id}")
async def analyze_meter(
    meter_id: int,
    data: PredictiveAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Анализ риска счётчика"""
    service = PredictiveService(db)
    return await service.analyze_meter(meter_id)


@router.post("/analyze/premise/{premise_id}")
async def analyze_premise(
    premise_id: int,
    data: PredictiveAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Анализ рисков помещения"""
    service = PredictiveService(db)
    return await service.analyze_premise(premise_id)


# ============================================
# Рейтинги рисков
# ============================================

@router.get("/risk/buildings")
async def get_building_risk_rating(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Рейтинг зданий по уровню риска"""
    service = PredictiveService(db)
    items = await service.get_risk_rating_buildings()
    return {"items": items, "total": len(items)}


@router.get("/risk/equipment")
async def get_equipment_risk_rating(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Рейтинг оборудования по вероятности поломки"""
    service = PredictiveService(db)
    items = await service.get_risk_rating_equipment()
    return {"items": items, "total": len(items)}


# ============================================
# Управление моделью
# ============================================

@router.post("/retrain", response_model=RetrainResponse)
async def retrain_model(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Переобучение предиктивной модели"""
    service = PredictiveService(db)
    return await service.retrain_model()


@router.get("/model-info", response_model=ModelInfoResponse)
async def get_model_info(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Информация о текущей модели"""
    service = PredictiveService(db)
    return await service.get_model_info()
