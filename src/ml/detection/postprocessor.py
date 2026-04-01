# -*- coding: utf-8 -*-
"""
Постобработка результатов детекции дефектов.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core.exceptions import MLException


@dataclass(slots=True, frozen=True)
class DetectionPostprocessConfig:
    """Конфигурация постобработки детекций."""

    min_confidence: float = 0.3
    nms_iou_threshold: float = 0.5
    merge_same_class_only: bool = True
    max_results: int = 100


@dataclass(slots=True, frozen=True)
class DetectionSummary:
    """Сводка по обработанным дефектам."""

    total_detections: int
    classes_count: dict[str, int]
    max_severity: int
    average_confidence: float
    risk_score: float


class DetectionPostprocessor:
    """Независимый постпроцессор для результатов YOLO-детекции."""

    def __init__(self, config: DetectionPostprocessConfig | None = None) -> None:
        self.config = config or DetectionPostprocessConfig()
        self._validate_config()

    def process(self, detections: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Запускает полный пайплайн постобработки.

        Этапы:
        1) валидация и нормализация
        2) пороговая фильтрация confidence
        3) NMS подавление дублей
        4) сортировка и ограничение количества
        5) расчёт сводки риска
        """

        try:
            normalized = self._validate_and_normalize(detections)
            filtered = [d for d in normalized if d["confidence"] >= self.config.min_confidence]
            suppressed = self._nms(filtered)
            ranked = sorted(
                suppressed,
                key=lambda d: (d.get("severity", 1), d["confidence"]),
                reverse=True,
            )
            limited = ranked[: self.config.max_results]
            summary = self._build_summary(limited)

            return {
                "detections": limited,
                "summary": {
                    "total_detections": summary.total_detections,
                    "classes_count": summary.classes_count,
                    "max_severity": summary.max_severity,
                    "average_confidence": summary.average_confidence,
                    "risk_score": summary.risk_score,
                },
            }
        except MLException:
            raise
        except Exception as exc:
            raise MLException(
                message=f"Ошибка постобработки детекций: {type(exc).__name__}: {exc}",
                model_name="detection_postprocessor",
            ) from exc

    def _validate_config(self) -> None:
        """Проверяет корректность параметров постобработки."""

        cfg = self.config

        if not (0.0 <= cfg.min_confidence <= 1.0):
            raise MLException(
                message="min_confidence должен быть в диапазоне [0, 1]",
                model_name="detection_postprocessor",
            )

        if not (0.0 < cfg.nms_iou_threshold <= 1.0):
            raise MLException(
                message="nms_iou_threshold должен быть в диапазоне (0, 1]",
                model_name="detection_postprocessor",
            )

        if cfg.max_results < 1:
            raise MLException(
                message="max_results должен быть >= 1",
                model_name="detection_postprocessor",
            )

    def _validate_and_normalize(self, detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Проверяет входные детекции и нормализует структуру полей."""

        if not isinstance(detections, list):
            raise MLException(
                message=f"Ожидался list детекций, получено: {type(detections).__name__}",
                model_name="detection_postprocessor",
            )

        normalized: list[dict[str, Any]] = []

        for item in detections:
            if not isinstance(item, dict):
                continue

            bbox = item.get("bbox")
            if not isinstance(bbox, dict):
                continue

            try:
                x1 = float(bbox.get("x1", 0.0))
                y1 = float(bbox.get("y1", 0.0))
                x2 = float(bbox.get("x2", 0.0))
                y2 = float(bbox.get("y2", 0.0))
            except (TypeError, ValueError):
                continue

            if x2 <= x1 or y2 <= y1:
                continue

            confidence = self._clamp01(item.get("confidence", 0.0))
            class_id = self._safe_int(item.get("class_id", -1), default=-1)
            class_code = str(item.get("class_code", "unknown")).strip() or "unknown"
            class_name_ru = str(item.get("class_name_ru", "Неизвестный дефект")).strip() or "Неизвестный дефект"
            severity = self._safe_int(item.get("severity", 1), default=1)
            severity = max(1, min(5, severity))

            normalized.append(
                {
                    "class_id": class_id,
                    "class_code": class_code,
                    "class_name_ru": class_name_ru,
                    "confidence": confidence,
                    "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                    "severity": severity,
                    "area": (x2 - x1) * (y2 - y1),
                }
            )

        return normalized

    def _nms(self, detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Простая реализация NMS для удаления пересекающихся дублей."""

        if not detections:
            return []

        # Сначала сортируем по confidence, чтобы лучший бокс выбирался первым.
        sorted_detections = sorted(detections, key=lambda d: d["confidence"], reverse=True)
        selected: list[dict[str, Any]] = []

        while sorted_detections:
            current = sorted_detections.pop(0)
            selected.append(current)

            remaining: list[dict[str, Any]] = []
            for candidate in sorted_detections:
                if self.config.merge_same_class_only and candidate["class_id"] != current["class_id"]:
                    remaining.append(candidate)
                    continue

                iou = self._iou(current["bbox"], candidate["bbox"])
                if iou < self.config.nms_iou_threshold:
                    remaining.append(candidate)

            sorted_detections = remaining

        return selected

    def _build_summary(self, detections: list[dict[str, Any]]) -> DetectionSummary:
        """Формирует агрегированную сводку для API/отчётов."""

        if not detections:
            return DetectionSummary(
                total_detections=0,
                classes_count={},
                max_severity=0,
                average_confidence=0.0,
                risk_score=0.0,
            )

        classes_count: dict[str, int] = {}
        confidence_sum = 0.0
        max_severity = 0

        for detection in detections:
            class_code = detection.get("class_code", "unknown")
            classes_count[class_code] = classes_count.get(class_code, 0) + 1

            confidence = float(detection.get("confidence", 0.0))
            confidence_sum += confidence

            severity = int(detection.get("severity", 1))
            max_severity = max(max_severity, severity)

        total = len(detections)
        average_confidence = confidence_sum / total if total > 0 else 0.0

        # Эвристическая оценка риска: средняя уверенность, умноженная на среднюю тяжесть.
        severity_mean = sum(int(d.get("severity", 1)) for d in detections) / total
        risk_score = min(5.0, average_confidence * severity_mean)

        return DetectionSummary(
            total_detections=total,
            classes_count=classes_count,
            max_severity=max_severity,
            average_confidence=round(average_confidence, 4),
            risk_score=round(risk_score, 4),
        )

    def _iou(self, a: dict[str, float], b: dict[str, float]) -> float:
        """Вычисляет IoU двух прямоугольников."""

        x_left = max(a["x1"], b["x1"])
        y_top = max(a["y1"], b["y1"])
        x_right = min(a["x2"], b["x2"])
        y_bottom = min(a["y2"], b["y2"])

        intersection_w = max(0.0, x_right - x_left)
        intersection_h = max(0.0, y_bottom - y_top)
        intersection_area = intersection_w * intersection_h

        area_a = max(0.0, (a["x2"] - a["x1"]) * (a["y2"] - a["y1"]))
        area_b = max(0.0, (b["x2"] - b["x1"]) * (b["y2"] - b["y1"]))

        union = area_a + area_b - intersection_area
        if union <= 0:
            return 0.0

        return intersection_area / union

    def _safe_int(self, value: Any, default: int) -> int:
        """Безопасно приводит значение к int."""

        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _clamp01(self, value: Any) -> float:
        """Приводит confidence к диапазону [0, 1]."""

        try:
            v = float(value)
        except (TypeError, ValueError):
            v = 0.0

        return max(0.0, min(1.0, v))
