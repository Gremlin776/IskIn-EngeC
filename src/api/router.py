# -*- coding: utf-8 -*-
"""
Главный роутер API
"""

from fastapi import APIRouter

from src.api.v1.endpoints import (
    health,
    buildings,
    premises,
    repair,
    meters,
    defects,
    reports,
    predictive,
    psd,
)

# Роутер API v1
api_router = APIRouter()

# Проверка работоспособности сервиса
api_router.include_router(health.router, tags=["Health"])

# Модули
api_router.include_router(
    buildings.router, prefix="/buildings", tags=["Buildings"])
api_router.include_router(
    premises.router, prefix="/premises", tags=["Premises"])
api_router.include_router(repair.router, prefix="/repair", tags=["Repair"])
api_router.include_router(meters.router, prefix="/meters", tags=["Meters"])
api_router.include_router(defects.router, prefix="/defects", tags=["Defects"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(
    predictive.router, prefix="/predictive", tags=["Predictive"])
api_router.include_router(psd.router, prefix="/psd", tags=["PSD"])
