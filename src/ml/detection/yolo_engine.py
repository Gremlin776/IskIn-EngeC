"""
YOLOv8 обёртка для детекции дефектов.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch

from src.core.exceptions import MLException
from src.ml.base import BaseMLModel, ModelMeta
from src.ml.detection.classes import DEFECT_CLASS_MAP, get_defect_class_info


@dataclass(slots=True, frozen=True)
class YOLOEngineConfig:
    """Конфигурация YOLO-движка детекции."""

    weights_path: str
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45
    image_size: int = 1280
    max_detections: int = 100
    gpu: bool = True
    half: bool = False
    augment: bool = False
    verbose: bool = False


class YOLODefectEngine(BaseMLModel[np.ndarray, list[dict[str, Any]]]):
    """Независимая обёртка YOLOv8 для детекции дефектов на изображениях."""

    def __init__(self, config: YOLOEngineConfig) -> None:
        self.config = config
        self._validate_config()

        self._model: Any | None = None
        self._device = self._resolve_device()

        super().__init__(
            meta=ModelMeta(
                name="yolo_defect_engine",
                version="yolov8",
                device=self._device,
            ),
            auto_load=False,
        )

    def _load(self) -> None:
        """Загружает YOLO-модель из весов на выбранное устройство."""

        weights_file = Path(self.config.weights_path)
        if not weights_file.exists() or not weights_file.is_file():
            raise MLException(
                message=f"Файл весов YOLO не найден: {weights_file}",
                model_name=self.meta.name,
            )

        try:
            from ultralytics import YOLO
        except Exception as exc:
            raise MLException(
                message=f"Не удалось импортировать ultralytics: {type(exc).__name__}: {exc}",
                model_name=self.meta.name,
            ) from exc

        try:
            self._model = YOLO(str(weights_file))
            self._model.to(self._device)
        except Exception as exc:
            raise MLException(
                message=f"Ошибка загрузки YOLO-весов: {type(exc).__name__}: {exc}",
                model_name=self.meta.name,
            ) from exc

    def _unload(self) -> None:
        """Освобождает ресурсы YOLO-движка."""

        self._model = None
        if self._device.startswith("cuda"):
            try:
                torch.cuda.empty_cache()
            except Exception:
                # Очистка кеша не должна ломать бизнес-процесс.
                pass

    def _validate_payload(self, payload: np.ndarray) -> None:
        """Проверяет корректность входного изображения."""

        if not isinstance(payload, np.ndarray):
            raise MLException(
                message=f"Ожидался np.ndarray, получено: {type(payload).__name__}",
                model_name=self.meta.name,
            )

        if payload.size == 0:
            raise MLException("Передано пустое изображение", model_name=self.meta.name)

        if payload.ndim not in (2, 3):
            raise MLException(
                message=f"Неподдерживаемая размерность изображения: {payload.ndim}",
                model_name=self.meta.name,
            )

        if payload.ndim == 3 and payload.shape[2] not in (1, 3, 4):
            raise MLException(
                message=f"Неподдерживаемое число каналов: {payload.shape[2]}",
                model_name=self.meta.name,
            )

    def _predict(self, payload: np.ndarray, **kwargs: Any) -> list[dict[str, Any]]:
        """Запускает инференс YOLO и возвращает стандартизированный список детекций."""

        if self._model is None:
            raise MLException("YOLO-движок не загружен", model_name=self.meta.name)

        conf = float(kwargs.get("confidence_threshold", self.config.confidence_threshold))
        iou = float(kwargs.get("iou_threshold", self.config.iou_threshold))
        imgsz = int(kwargs.get("image_size", self.config.image_size))
        max_det = int(kwargs.get("max_detections", self.config.max_detections))

        try:
            results = self._model.predict(
                source=payload,
                conf=conf,
                iou=iou,
                imgsz=imgsz,
                max_det=max_det,
                augment=bool(kwargs.get("augment", self.config.augment)),
                device=self._device,
                half=bool(kwargs.get("half", self.config.half)),
                verbose=bool(kwargs.get("verbose", self.config.verbose)),
            )
        except Exception as exc:
            raise MLException(
                message=f"Ошибка инференса YOLO: {type(exc).__name__}: {exc}",
                model_name=self.meta.name,
            ) from exc

        return self._normalize_results(results)

    def _warmup(self, sample: np.ndarray | None = None) -> None:
        """Прогревает YOLO-модель фиктивным кадром."""

        if self._model is None:
            raise MLException("YOLO-движок не загружен", model_name=self.meta.name)

        warmup_image = sample
        if warmup_image is None:
            warmup_image = np.zeros((640, 640, 3), dtype=np.uint8)

        self._validate_payload(warmup_image)
        try:
            _ = self._model.predict(
                source=warmup_image,
                conf=self.config.confidence_threshold,
                iou=self.config.iou_threshold,
                imgsz=self.config.image_size,
                max_det=10,
                device=self._device,
                verbose=False,
            )
        except Exception as exc:
            raise MLException(
                message=f"Ошибка прогрева YOLO-движка: {type(exc).__name__}: {exc}",
                model_name=self.meta.name,
            ) from exc

    def _resolve_device(self) -> str:
        """Определяет устройство выполнения инференса."""

        if self.config.gpu and torch.cuda.is_available():
            return "cuda:0"
        return "cpu"

    def _validate_config(self) -> None:
        """Валидирует конфигурацию до запуска модели."""

        cfg = self.config

        if not cfg.weights_path.strip():
            raise MLException("weights_path не может быть пустым", model_name="yolo_defect_engine")

        if not (0.0 < cfg.confidence_threshold <= 1.0):
            raise MLException(
                message="confidence_threshold должен быть в диапазоне (0, 1]",
                model_name="yolo_defect_engine",
            )

        if not (0.0 < cfg.iou_threshold <= 1.0):
            raise MLException(
                message="iou_threshold должен быть в диапазоне (0, 1]",
                model_name="yolo_defect_engine",
            )

        if cfg.image_size < 64:
            raise MLException("image_size должен быть >= 64", model_name="yolo_defect_engine")

        if cfg.max_detections < 1:
            raise MLException("max_detections должен быть >= 1", model_name="yolo_defect_engine")

    def _normalize_results(self, results: Any) -> list[dict[str, Any]]:
        """Преобразует ответ Ultralytics в единый API-формат."""

        detections: list[dict[str, Any]] = []

        if not results:
            return detections

        for frame_result in results:
            boxes = getattr(frame_result, "boxes", None)
            if boxes is None:
                continue

            try:
                xyxy = boxes.xyxy.detach().cpu().numpy()
                conf = boxes.conf.detach().cpu().numpy()
                cls = boxes.cls.detach().cpu().numpy()
            except Exception as exc:
                raise MLException(
                    message=f"Ошибка чтения боксов YOLO: {type(exc).__name__}: {exc}",
                    model_name=self.meta.name,
                ) from exc

            for idx in range(len(xyxy)):
                class_id = int(cls[idx])
                score = float(conf[idx])
                x1, y1, x2, y2 = [float(v) for v in xyxy[idx].tolist()]

                class_info = DEFECT_CLASS_MAP.get(class_id)
                if class_info is None:
                    # Неизвестный класс не ломает пайплайн, но маркируется явно.
                    class_code = "unknown"
                    class_name_ru = "Неизвестный дефект"
                    severity = 1
                else:
                    info = get_defect_class_info(class_id)
                    class_code = info.code
                    class_name_ru = info.name_ru
                    severity = info.severity_default

                detections.append(
                    {
                        "class_id": class_id,
                        "class_code": class_code,
                        "class_name_ru": class_name_ru,
                        "confidence": max(0.0, min(1.0, score)),
                        "bbox": {
                            "x1": x1,
                            "y1": y1,
                            "x2": x2,
                            "y2": y2,
                        },
                        "severity": severity,
                    }
                )

        return detections
