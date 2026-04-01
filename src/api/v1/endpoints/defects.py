# -*- coding: utf-8 -*-
"""
Эндпоинты для модуля детекции дефектов конструкций
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pathlib import Path
import shutil
import uuid
import time
import base64
import io

from src.core.config import get_settings
from src.api.deps import CurrentUser, get_current_user, get_db
from src.services.defect_service import DefectService
from src.api.v1.schemas.defect import (
    InspectionCreate, InspectionUpdate, InspectionResponse,
    DefectResponse, DefectReviewRequest, DefectStatsResponse,
    DefectClassCreate, DefectClassResponse,
    DetectResponse, DetectedDefectItem, BoundingBox,
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


# ============================================
# YOLO Детекция дефектов (inference)
# ============================================

@router.post("/detect", response_model=DetectResponse)
async def detect_defects(
    file: UploadFile = File(...,
                            description="Изображение для анализа дефектов"),
    confidence_threshold: float = Query(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Порог уверенности детекции (0.0-1.0)"
    ),
    inspection_id: Optional[int] = Query(
        default=None,
        description="ID обследования (опционально, для сохранения в БД)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Детекция дефектов на изображении с помощью YOLOv8.

    Принимает изображение (JPEG, PNG) и возвращает найденные дефекты
    с bounding boxes, классами и уверенностью.

    Если указан inspection_id — сохраняет результаты в БД.
    """
    from src.ml.detection.yolo_engine import YOLODefectEngine, YOLOEngineConfig
    from src.models.defect import DetectedDefect as DetectedDefectModel
    from sqlalchemy import select
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw
    from src.ml.detection.classes import DEFECT_CLASS_MAP, get_defect_class_info

    # Время начала обработки
    start_time = time.time()

    # Сохраняем временный файл
    upload_dir = Path(settings.upload_dir) / "temp"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = upload_dir / file_name

    try:
        # Сохранение файла
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Чтение изображения
        image_bgr = cv2.imread(str(file_path))
        if image_bgr is None:
            raise HTTPException(
                status_code=400,
                detail="Не удалось прочитать изображение. Проверьте формат файла."
            )

        # Получаем оригинальные размеры
        img_height, img_width = image_bgr.shape[:2]

        # Инициализация YOLO движка
        model_path = Path("models/yolo/best.pt")
        if not model_path.exists():
            raise HTTPException(
                status_code=503,
                detail="Модель YOLO не найдена. Требуется обучение модели."
            )

        config = YOLOEngineConfig(
            weights_path=str(model_path),
            confidence_threshold=confidence_threshold,
            iou_threshold=0.45,
            image_size=256,
            max_detections=100,
            gpu=True,
            half=False,
            verbose=False,
        )

        engine = YOLODefectEngine(config)

        # Запуск детекции
        detections = engine.detect(image_bgr)

        # Отрисовка bounding boxes на изображении
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        draw = ImageDraw.Draw(pil_image)

        # Формирование ответа
        detected_defects = []

        for det in detections:
            # Извлекаем данные детекции
            class_id = det["class_id"]
            class_info = get_defect_class_info(class_id)
            confidence = det["confidence"]
            bbox = det["bbox"]

            # Конвертируем bbox из [x1, y1, x2, y2] в [x, y, width, height]
            x1, y1, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
            width = x2 - x1
            height = y2 - y1

            # Определяем severity
            severity_map = {1: "low", 2: "medium",
                            3: "medium", 4: "high", 5: "critical"}
            severity = severity_map.get(det.get("severity", 2), "medium")

            # Добавляем в список
            detected_defects.append(DetectedDefectItem(
                class_name=class_info.code,
                class_name_ru=class_info.name_ru,
                confidence=confidence,
                bbox=BoundingBox(
                    x=float(x1),
                    y=float(y1),
                    width=float(width),
                    height=float(height),
                ),
                severity=severity,
            ))

            # Рисуем bounding box
            draw.rectangle([x1, y1, x2, y2], outline="#FF0000", width=3)
            draw.text(
                (x1, y1 - 10),
                f"{class_info.name_ru} {confidence:.2f}",
                fill="#FF0000"
            )

        # Конвертируем изображение с bbox в base64
        buffer = io.BytesIO()
        pil_image.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode("utf-8")

        # Сохранение в БД если указан inspection_id
        if inspection_id:
            # Проверяем существование обследования
            from src.models.defect import Inspection
            result = await db.execute(
                select(Inspection).where(Inspection.id == inspection_id)
            )
            inspection = result.scalar_one_or_none()

            if inspection is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Обследование {inspection_id} не найдено"
                )

            # Создаем фото обследования
            from src.models.defect import InspectionPhoto
            photo = InspectionPhoto(
                inspection_id=inspection_id,
                file_path=str(file_path),
                file_name=file_name,
                description="Фото с YOLO детекцией",
            )
            db.add(photo)
            await db.flush()  # Получаем photo.id

            # Получаем или создаем класс дефекта
            from src.models.defect import DefectClass
            for det in detections:
                class_id = det["class_id"]
                class_info = get_defect_class_info(class_id)

                # Ищем существующий класс
                result = await db.execute(
                    select(DefectClass).where(
                        DefectClass.code == class_info.code)
                )
                defect_class = result.scalar_one_or_none()

                if defect_class is None:
                    # Создаем новый класс
                    severity_map = {1: "low", 2: "medium",
                                    3: "medium", 4: "high", 5: "critical"}
                    defect_class = DefectClass(
                        name=class_info.name_ru,
                        code=class_info.code,
                        yolo_class_id=class_id,
                        description=f"Автоматически созданный класс для YOLO детекции",
                        severity_level=det.get("severity", 2),
                        color="#FF0000",
                    )
                    db.add(defect_class)
                    await db.flush()

                # Конвертируем bbox
                x1, y1, x2, y2 = det["bbox"]["x1"], det["bbox"]["y1"], det["bbox"]["x2"], det["bbox"]["y2"]

                # Создаем дефект
                severity_map = {1: "low", 2: "medium",
                                3: "medium", 4: "high", 5: "critical"}
                db_defect = DetectedDefectModel(
                    inspection_id=inspection_id,
                    photo_id=photo.id,
                    defect_class_id=defect_class.id,
                    confidence=det["confidence"],
                    bbox_x=int(x1),
                    bbox_y=int(y1),
                    bbox_width=int(x2 - x1),
                    bbox_height=int(y2 - y1),
                    severity=severity_map.get(
                        det.get("severity", 2), "medium"),
                    status="detected",
                )
                db.add(db_defect)

            await db.commit()

        # Время обработки
        processing_time_ms = (time.time() - start_time) * 1000

        return DetectResponse(
            defects=detected_defects,
            total_defects=len(detected_defects),
            processing_time_ms=round(processing_time_ms, 2),
            image_with_boxes=image_base64,
        )

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при детекции дефектов: {str(e)}"
        )
    finally:
        # Очистка временного файла (если не сохранено в БД)
        if not inspection_id and file_path.exists():
            file_path.unlink(missing_ok=True)
