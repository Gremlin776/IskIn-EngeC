# -*- coding: utf-8 -*-
"""
Эндпоинты для сравнения ПСД и классификации ремонтов.
"""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import json

from src.api.deps import CurrentUser, get_current_user, get_db
from src.ml.nlp.psd_comparator import PSDComparator
from src.ml.nlp.repair_classifier import RepairClassifier

router = APIRouter()


# ============================================
# Сравнение ПСД
# ============================================

@router.post("/compare", summary="Сравнить ведомость с ПСД")
async def compare_psd(
    work_order: UploadFile = File(..., description="Файл ведомости (txt, xlsx, docx, pdf)"),
    psd: UploadFile = File(..., description="Файл проектно-сметной документации"),
    similarity_threshold: float = Query(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Порог similarity для совпадений"
    ),
    deviation_threshold: float = Query(
        default=10.0,
        ge=0.0,
        le=100.0,
        description="Порог отклонения объёмов (%)"
    ),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Сравнить ведомость выполненных работ с проектно-сметной документацией.
    
    **Алгоритм:**
    1. Парсинг строк ведомости и сметы
    2. TF-IDF векторизация описаний (русский язык)
    3. Cosine similarity для поиска совпадений
    4. Сравнение объёмов и расчёт отклонений
    
    **Поддерживаемые форматы:**
    - TXT (простой текст)
    - XLSX (Excel через openpyxl)
    - DOCX (Word через python-docx)
    - PDF (PyMuPDF/fitz)
    
    **Возвращает:**
    - matches: Список сопоставлений
    - total_items: Всего элементов в ведомости
    - matched: Найдено совпадений
    - deviations_found: Найдено расхождений
    - not_found: Не найдено в ПСД
    - overall_match_pct: Общий процент совпадения
    """
    try:
        # Чтение файлов
        work_order_text = await _read_upload_file(work_order)
        psd_text = await _read_upload_file(psd)
        
        # Сравнение
        comparator = PSDComparator()
        comparator.SIMILARITY_THRESHOLD = similarity_threshold
        comparator.DEVIATION_THRESHOLD = deviation_threshold
        
        report = comparator.compare(work_order_text, psd_text)
        result = comparator.to_dict(report)
        
        return result
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        raise HTTPException(status_code=501, detail=f"Необходима установка зависимости: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при сравнении: {str(e)}")


@router.post("/compare-text", summary="Сравнить текст ведомости с текстом ПСД")
async def compare_psd_text(
    work_order_text: str = Query(..., description="Текст ведомости (каждая строка с новой строки)"),
    psd_text: str = Query(..., description="Текст ПСД (каждая строка с новой строки)"),
    similarity_threshold: float = Query(default=0.65),
    deviation_threshold: float = Query(default=10.0),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Сравнить тексты ведомости и ПД (через query параметры).
    
    Удобно для тестирования через Swagger UI.
    """
    try:
        comparator = PSDComparator()
        comparator.SIMILARITY_THRESHOLD = similarity_threshold
        comparator.DEVIATION_THRESHOLD = deviation_threshold
        
        report = comparator.compare(work_order_text, psd_text)
        result = comparator.to_dict(report)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Классификация ремонтов
# ============================================

@router.post("/suggest-type", summary="Предложить тип ремонта")
async def suggest_repair_type(
    text: str = Query(..., description="Текст описания проблемы", max_length=1000),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Автоматически определить тип ремонта по тексту заявки.
    
    **Пример:**
    - Вход: "Течёт кран на кухне"
    - Выход: {"type_code": "plumbing", "type_name": "Сантехника", "confidence": 0.85}
    
    **Поддерживаемые типы:**
    - plumbing: Сантехника
    - electrical: Электрика
    - hvac: Отопление/Вентиляция
    - finishing: Отделочные работы
    - structural: Строительные работы
    - elevator: Лифтовое оборудование
    - fire_safety: Пожарная безопасность
    - other: Прочее
    """
    try:
        classifier = RepairClassifier()
        result = classifier.suggest_type(text)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repair-types", summary="Получить все типы ремонтов")
async def get_repair_types(
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Получить справочник всех типов ремонтов.
    
    Возвращает список с кодами, названиями и ключевыми словами.
    """
    classifier = RepairClassifier()
    return {"types": classifier.get_all_types()}


# ============================================
# Вспомогательные функции
# ============================================

async def _read_upload_file(file: UploadFile) -> str:
    """
    Прочитать содержимое UploadFile.
    
    Args:
        file: Загруженный файл
        
    Returns:
        Текст файла
    """
    contents = await file.read()
    
    # Пробуем разные кодировки
    for encoding in ['utf-8', 'cp1251', 'latin-1']:
        try:
            return contents.decode(encoding)
        except UnicodeDecodeError:
            continue
    
    # Если не удалось декодировать
    raise HTTPException(
        status_code=400,
        detail=f"Не удалось прочитать файл {file.filename}. Проверьте кодировку (требуется UTF-8 или Windows-1251)."
    )
