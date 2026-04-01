# -*- coding: utf-8 -*-
"""
Базовые интерфейсы и общая инфраструктура для ML-модулей проекта.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Generic, TypeVar

from src.core.exceptions import MLException

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class ModelState(StrEnum):
    """Состояние ML-модели в рантайме."""

    NOT_LOADED = "not_loaded"
    LOADED = "loaded"
    FAILED = "failed"


@dataclass(slots=True, frozen=True)
class ModelMeta:
    """Метаданные модели для логирования и диагностики."""

    name: str
    version: str = "unknown"
    device: str = "cpu"


class BaseMLModel(ABC, Generic[InputT, OutputT]):
    """
    Базовый интерфейс для всех ML-моделей.

    Наследник реализует только доменную логику в protected-методах,
    а все проверки и оборачивание ошибок уже обеспечивает базовый класс.
    """

    def __init__(
        self,
        meta: ModelMeta,
        *,
        auto_load: bool = False,
    ) -> None:
        if not meta.name.strip():
            raise MLException("Имя модели не может быть пустым", model_name="unknown")

        self.meta = meta
        self.state = ModelState.NOT_LOADED

        if auto_load:
            self.load()

    @property
    def is_loaded(self) -> bool:
        """Флаг готовности модели к инференсу."""

        return self.state == ModelState.LOADED

    def load(self) -> None:
        """Безопасная загрузка модели в память/GPU."""

        if self.is_loaded:
            return

        try:
            self._load()
            self.state = ModelState.LOADED
        except MLException:
            self.state = ModelState.FAILED
            raise
        except Exception as exc:
            self.state = ModelState.FAILED
            raise self._wrap_error("Ошибка загрузки модели", exc) from exc

    def unload(self) -> None:
        """Освобождает ресурсы модели."""

        if self.state == ModelState.NOT_LOADED:
            return

        try:
            self._unload()
            self.state = ModelState.NOT_LOADED
        except MLException:
            self.state = ModelState.FAILED
            raise
        except Exception as exc:
            self.state = ModelState.FAILED
            raise self._wrap_error("Ошибка выгрузки модели", exc) from exc

    def predict(self, payload: InputT, **kwargs: Any) -> OutputT:
        """
        Выполняет инференс с единым pipeline обработки ошибок.

        Порядок:
        1) lazy-load модели
        2) валидация входа
        3) инференс
        4) постобработка
        """

        try:
            if not self.is_loaded:
                self.load()

            self._validate_payload(payload)
            raw_result = self._predict(payload, **kwargs)
            return self._postprocess(raw_result)
        except MLException:
            raise
        except Exception as exc:
            self.state = ModelState.FAILED
            raise self._wrap_error("Ошибка инференса", exc) from exc

    def healthcheck(self) -> dict[str, Any]:
        """Возвращает минимальную диагностику состояния модели."""

        return {
            "name": self.meta.name,
            "version": self.meta.version,
            "device": self.meta.device,
            "state": self.state.value,
            "is_loaded": self.is_loaded,
        }

    def warmup(self, sample: InputT | None = None) -> None:
        """Опциональный прогрев модели для уменьшения задержек первого запроса."""

        if not self.is_loaded:
            self.load()

        try:
            self._warmup(sample)
        except MLException:
            raise
        except Exception as exc:
            raise self._wrap_error("Ошибка прогрева модели", exc) from exc

    @abstractmethod
    def _load(self) -> None:
        """Реальная загрузка модели. Обязательно для реализации."""

    @abstractmethod
    def _predict(self, payload: InputT, **kwargs: Any) -> OutputT:
        """Реальный инференс. Обязательно для реализации."""

    def _unload(self) -> None:
        """Опциональная логика освобождения ресурсов."""

    def _validate_payload(self, payload: InputT) -> None:
        """Опциональная валидация входных данных перед инференсом."""

    def _postprocess(self, raw_result: OutputT) -> OutputT:
        """Опциональная постобработка результата инференса."""

        return raw_result

    def _warmup(self, sample: InputT | None = None) -> None:
        """Опциональная реализация прогрева модели."""

    def _wrap_error(self, message: str, exc: Exception) -> MLException:
        """Унифицированное формирование ML-ошибки с контекстом."""

        details = f"{message}: {type(exc).__name__}: {exc}"
        return MLException(message=details, model_name=self.meta.name)
