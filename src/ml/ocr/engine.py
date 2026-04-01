# -*- coding: utf-8 -*-
"""
EasyOCR обёртка для распознавания показаний счётчиков.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import torch

from src.core.exceptions import MLException
from src.ml.base import BaseMLModel, ModelMeta


@dataclass(slots=True, frozen=True)
class EasyOCREngineConfig:
    """Конфигурация OCR-движка."""

    languages: tuple[str, ...] = ("en",)
    gpu: bool = True
    model_storage_directory: str | None = None
    user_network_directory: str | None = None
    detector: bool = True
    recognizer: bool = True
    download_enabled: bool = False

    # Параметры распознавания
    detail: int = 1
    paragraph: bool = False
    allowlist: str = "0123456789"
    width_ths: float = 0.5
    height_ths: float = 0.5
    decoder: str = "greedy"
    batch_size: int = 1


class EasyOCREngine(BaseMLModel[np.ndarray, list[dict[str, Any]]]):
    """Независимая обёртка EasyOCR в формате базового ML-интерфейса."""

    def __init__(self, config: EasyOCREngineConfig | None = None) -> None:
        self.config = config or EasyOCREngineConfig()
        self._validate_config()

        self._reader: Any | None = None
        self._device = self._resolve_device()

        super().__init__(
            meta=ModelMeta(
                name="easyocr_engine",
                version="easyocr",
                device=self._device,
            ),
            auto_load=False,
        )

    def _load(self) -> None:
        """Инициализирует EasyOCR Reader с учётом GPU/CPU конфигурации."""

        try:
            import easyocr
        except Exception as exc:
            raise MLException(
                message=f"Не удалось импортировать easyocr: {type(exc).__name__}: {exc}",
                model_name=self.meta.name,
            ) from exc

        try:
            use_gpu = self.config.gpu and self._device.startswith("cuda")
            self._reader = easyocr.Reader(
                list(self.config.languages),
                gpu=use_gpu,
                model_storage_directory=self.config.model_storage_directory,
                user_network_directory=self.config.user_network_directory,
                detector=self.config.detector,
                recognizer=self.config.recognizer,
                download_enabled=self.config.download_enabled,
            )
        except MLException:
            raise
        except Exception as exc:
            raise MLException(
                message=f"Ошибка инициализации EasyOCR Reader: {type(exc).__name__}: {exc}",
                model_name=self.meta.name,
            ) from exc

    def _unload(self) -> None:
        """Освобождает ресурсы OCR-движка."""

        self._reader = None
        if self._device.startswith("cuda"):
            try:
                torch.cuda.empty_cache()
            except Exception:
                # Очистка кеша не должна ломать бизнес-процесс.
                pass

    def _validate_payload(self, payload: np.ndarray) -> None:
        """Проверяет вход перед OCR инференсом."""

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

    def _predict(self, payload: np.ndarray, **kwargs: Any) -> list[dict[str, Any]]:
        """Выполняет OCR распознавание и возвращает стандартизированный результат."""

        if self._reader is None:
            raise MLException("OCR-движок не загружен", model_name=self.meta.name)

        try:
            raw_result = self._reader.readtext(
                payload,
                detail=kwargs.get("detail", self.config.detail),
                paragraph=kwargs.get("paragraph", self.config.paragraph),
                allowlist=kwargs.get("allowlist", self.config.allowlist),
                width_ths=kwargs.get("width_ths", self.config.width_ths),
                height_ths=kwargs.get("height_ths", self.config.height_ths),
                decoder=kwargs.get("decoder", self.config.decoder),
                batch_size=kwargs.get("batch_size", self.config.batch_size),
            )
        except Exception as exc:
            raise MLException(
                message=f"Ошибка OCR инференса: {type(exc).__name__}: {exc}",
                model_name=self.meta.name,
            ) from exc

        return self._normalize_result(raw_result)

    def _warmup(self, sample: np.ndarray | None = None) -> None:
        """Прогревает модель фиктивным кадром для снижения первого latency."""

        if self._reader is None:
            raise MLException("OCR-движок не загружен", model_name=self.meta.name)

        warmup_image = sample
        if warmup_image is None:
            warmup_image = np.zeros((64, 256), dtype=np.uint8)

        self._validate_payload(warmup_image)
        try:
            _ = self._reader.readtext(
                warmup_image,
                detail=self.config.detail,
                paragraph=self.config.paragraph,
                allowlist=self.config.allowlist,
                decoder=self.config.decoder,
                batch_size=self.config.batch_size,
            )
        except Exception as exc:
            raise MLException(
                message=f"Ошибка прогрева OCR-движка: {type(exc).__name__}: {exc}",
                model_name=self.meta.name,
            ) from exc

    def _resolve_device(self) -> str:
        """Определяет целевое устройство инференса."""

        if self.config.gpu and torch.cuda.is_available():
            return "cuda:0"
        return "cpu"

    def _validate_config(self) -> None:
        """Проверяет конфигурацию OCR-движка до старта."""

        if not self.config.languages:
            raise MLException("Список языков OCR не может быть пустым", model_name="easyocr_engine")

        if self.config.batch_size < 1:
            raise MLException("batch_size должен быть >= 1", model_name="easyocr_engine")

        if self.config.detail not in (0, 1):
            raise MLException("detail должен быть 0 или 1", model_name="easyocr_engine")

        if self.config.width_ths <= 0 or self.config.height_ths <= 0:
            raise MLException(
                "width_ths и height_ths должны быть > 0",
                model_name="easyocr_engine",
            )

    def _normalize_result(self, raw_result: Any) -> list[dict[str, Any]]:
        """Приводит ответ EasyOCR к единому структурированному формату."""

        normalized: list[dict[str, Any]] = []

        if not isinstance(raw_result, list):
            return normalized

        for item in raw_result:
            if not isinstance(item, (list, tuple)):
                continue

            if len(item) >= 3:
                bbox = item[0]
                text = str(item[1]).strip()
                confidence = float(item[2]) if item[2] is not None else 0.0
            elif len(item) == 2:
                bbox = item[0]
                text = str(item[1]).strip()
                confidence = 0.0
            else:
                continue

            normalized.append(
                {
                    "bbox": bbox,
                    "text": text,
                    "confidence": max(0.0, min(1.0, confidence)),
                }
            )

        return normalized
