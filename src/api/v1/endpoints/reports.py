# -*- coding: utf-8 -*-
"""
Эндпоинты для модуля генерации отчётов
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pathlib import Path

from src.api.deps import CurrentUser, get_current_user, get_db
from src.services.report_service import ReportService
from src.api.v1.schemas.report import (
    ReportCreate, ReportResponse,
    ReportGenerateRequest,
    ReportTemplateCreate, ReportTemplateResponse,
)

router = APIRouter()


# ============================================
# Шаблоны
# ============================================

@router.get("/templates", response_model=list[ReportTemplateResponse])
async def get_templates(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получение шаблонов отчётов"""
    service = ReportService(db)
    return await service.get_templates()


@router.post("/templates", response_model=ReportTemplateResponse,
             status_code=status.HTTP_201_CREATED)
async def create_template(
    data: ReportTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Создание шаблона"""
    service = ReportService(db)
    return await service.create_template(**data.model_dump())


# ============================================
# Отчёты
# ============================================

@router.get("/", response_model=list[ReportResponse])
async def get_reports(
    report_type: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получение списка отчётов"""
    service = ReportService(db)
    return await service.get_all(skip=skip, limit=limit)


@router.post("/", response_model=ReportResponse,
             status_code=status.HTTP_201_CREATED)
async def create_report(
    data: ReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Создание отчёта вручную"""
    service = ReportService(db)
    return await service.create_manual_report(
        user_id=current_user.id,
        **data.model_dump()
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Получение отчёта по ID"""
    service = ReportService(db)
    report = await service.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Отчёт не найден")
    return report


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Удаление отчёта"""
    service = ReportService(db)
    deleted = await service.delete_report(report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Отчёт не найден")


@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Скачать файл отчёта"""
    service = ReportService(db)
    report = await service.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Отчёт не найден")
    if not report.file_path or not Path(report.file_path).exists():
        raise HTTPException(status_code=404, detail="Файл отчёта не найден")
    return FileResponse(
        path=report.file_path,
        filename=Path(report.file_path).name,
    )


# ============================================
# Генерация через LLM
# ============================================

@router.post("/generate/repair", response_model=ReportResponse,
             status_code=status.HTTP_201_CREATED)
async def generate_repair_report(
    data: ReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Генерация отчёта по ремонту через LLM"""
    service = ReportService(db)
    return await service.generate_repair_report(
        user_id=current_user.id,
        repair_request_id=data.entity_id,
    )


@router.post("/generate/inspection", response_model=ReportResponse,
             status_code=status.HTTP_201_CREATED)
async def generate_inspection_report(
    data: ReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Генерация отчёта по обследованию через LLM"""
    service = ReportService(db)
    return await service.generate_inspection_report(
        user_id=current_user.id,
        inspection_id=data.entity_id,
    )


@router.post("/generate/monthly", response_model=ReportResponse,
             status_code=status.HTTP_201_CREATED)
async def generate_monthly_report(
    data: ReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Генерация ежемесячного отчёта"""
    service = ReportService(db)
    return await service.generate_monthly_report(
        user_id=current_user.id,
        period_start=data.period_start,
        period_end=data.period_end,
    )
