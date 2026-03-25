"""
Модель прогнозирования отказов оборудования.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import torch
from torch import Tensor, nn

from src.core.exceptions import MLException
from src.ml.base import BaseMLModel, ModelMeta


@dataclass(slots=True, frozen=True)
class ForecasterConfig:
    """Конфигурация predictive-модели."""

    input_size: int
    hidden_sizes: tuple[int, ...] = (64, 32)
    dropout: float = 0.15
    gpu: bool = True
    weights_path: str | None = None
    probability_threshold_high: float = 0.7
    probability_threshold_medium: float = 0.4
    use_heuristic_if_untrained: bool = True


@dataclass(slots=True, frozen=True)
class ForecastResult:
    """Структурированный ответ модели прогнозирования."""

    failure_probability: float
    confidence_level: str
    risk_score: float
    predicted_failure_date: date | None
    days_to_failure: int | None
    model_version: str
    risk_factors: list[str]


class PredictiveMLP(nn.Module):
    """Компактная MLP-модель бинарного риска отказа."""

    def __init__(
        self,
        input_size: int,
        hidden_sizes: tuple[int, ...],
        dropout: float,
    ) -> None:
        super().__init__()

        layers: list[nn.Module] = []
        prev_size = input_size

        for hidden_size in hidden_sizes:
            layers.append(nn.Linear(prev_size, hidden_size))
            layers.append(nn.ReLU())
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            prev_size = hidden_size

        layers.append(nn.Linear(prev_size, 1))
        self.network = nn.Sequential(*layers)

    def forward(self, x: Tensor) -> Tensor:
        logits = self.network(x)
        return torch.sigmoid(logits)


class FailureForecaster(BaseMLModel[dict[str, float] | list[float] | tuple[float, ...], ForecastResult]):
    """Независимый модуль прогнозирования вероятности отказа оборудования."""

    def __init__(self, config: ForecasterConfig) -> None:
        self.config = config
        self._validate_config()

        self._device = self._resolve_device()
        self._model: PredictiveMLP | None = None
        self._is_trained_weights_loaded = False

        super().__init__(
            meta=ModelMeta(
                name="failure_forecaster",
                version="predictive_mlp_v1",
                device=self._device,
            ),
            auto_load=False,
        )

    def _load(self) -> None:
        """Инициализирует модель и при наличии загружает веса."""

        try:
            self._model = PredictiveMLP(
                input_size=self.config.input_size,
                hidden_sizes=self.config.hidden_sizes,
                dropout=self.config.dropout,
            ).to(self._device)
            self._model.eval()
        except Exception as exc:
            raise MLException(
                message=f"Ошибка инициализации predictive-модели: {type(exc).__name__}: {exc}",
                model_name=self.meta.name,
            ) from exc

        weights_path = self.config.weights_path
        if weights_path:
            path = Path(weights_path)
            if not path.exists() or not path.is_file():
                raise MLException(
                    message=f"Файл весов predictive-модели не найден: {path}",
                    model_name=self.meta.name,
                )
            self.load_weights(str(path))

    def _unload(self) -> None:
        """Освобождает ресурсы модели."""

        self._model = None
        self._is_trained_weights_loaded = False
        if self._device.startswith("cuda"):
            try:
                torch.cuda.empty_cache()
            except Exception:
                # Очистка кеша не должна ломать бизнес-процесс.
                pass

    def _validate_payload(self, payload: dict[str, float] | list[float] | tuple[float, ...]) -> None:
        """Проверяет входной вектор признаков."""

        vector = self._to_feature_vector(payload)
        if len(vector) != self.config.input_size:
            raise MLException(
                message=(
                    "Некорректный размер вектора признаков: "
                    f"{len(vector)} (ожидалось {self.config.input_size})"
                ),
                model_name=self.meta.name,
            )

    def _predict(
        self,
        payload: dict[str, float] | list[float] | tuple[float, ...],
        **kwargs: Any,
    ) -> ForecastResult:
        """Выполняет прогноз отказа и возвращает нормализованный результат."""

        vector = self._to_feature_vector(payload)

        if len(vector) != self.config.input_size:
            raise MLException(
                message=(
                    "Некорректный размер вектора признаков: "
                    f"{len(vector)} (ожидалось {self.config.input_size})"
                ),
                model_name=self.meta.name,
            )

        probability = self._predict_probability(vector)

        # Дополнительная калибровка при необходимости из kwargs.
        calibration_shift = self._safe_float(kwargs.get("calibration_shift", 0.0))
        probability = max(0.0, min(1.0, probability + calibration_shift))

        risk_score = round(probability * 5.0, 4)
        confidence_level = self._confidence_level(probability)
        days_to_failure = self._estimate_days_to_failure(probability)

        base_date = kwargs.get("reference_date")
        ref_date = self._normalize_date(base_date) or date.today()
        predicted_failure_date = ref_date + timedelta(days=days_to_failure) if days_to_failure is not None else None

        risk_factors = self._extract_risk_factors_from_dict(payload)

        return ForecastResult(
            failure_probability=round(probability, 6),
            confidence_level=confidence_level,
            risk_score=risk_score,
            predicted_failure_date=predicted_failure_date,
            days_to_failure=days_to_failure,
            model_version=self.meta.version,
            risk_factors=risk_factors,
        )

    def _warmup(self, sample: dict[str, float] | list[float] | tuple[float, ...] | None = None) -> None:
        """Прогревает модель фиктивным вектором признаков."""

        if self._model is None and not self.config.use_heuristic_if_untrained:
            raise MLException("Predictive-модель не загружена", model_name=self.meta.name)

        vector = sample if sample is not None else [0.0] * self.config.input_size
        self._validate_payload(vector)

        try:
            _ = self._predict_probability(self._to_feature_vector(vector))
        except Exception as exc:
            raise MLException(
                message=f"Ошибка прогрева predictive-модели: {type(exc).__name__}: {exc}",
                model_name=self.meta.name,
            ) from exc

    def load_weights(self, weights_path: str) -> None:
        """Загружает state_dict модели из файла."""

        if self._model is None:
            raise MLException("Модель не инициализирована", model_name=self.meta.name)

        path = Path(weights_path)
        if not path.exists() or not path.is_file():
            raise MLException(
                message=f"Файл весов не найден: {path}",
                model_name=self.meta.name,
            )

        try:
            state_dict = torch.load(path, map_location=self._device)
            if not isinstance(state_dict, dict):
                raise MLException(
                    message="Некорректный формат файла весов (ожидался state_dict)",
                    model_name=self.meta.name,
                )
            self._model.load_state_dict(state_dict)
            self._model.eval()
            self._is_trained_weights_loaded = True
        except MLException:
            raise
        except Exception as exc:
            raise MLException(
                message=f"Ошибка загрузки весов: {type(exc).__name__}: {exc}",
                model_name=self.meta.name,
            ) from exc

    def save_weights(self, output_path: str) -> None:
        """Сохраняет текущий state_dict модели."""

        if self._model is None:
            raise MLException("Модель не инициализирована", model_name=self.meta.name)

        path = Path(output_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            torch.save(self._model.state_dict(), path)
        except Exception as exc:
            raise MLException(
                message=f"Ошибка сохранения весов: {type(exc).__name__}: {exc}",
                model_name=self.meta.name,
            ) from exc

    def _predict_probability(self, feature_vector: list[float]) -> float:
        """Возвращает вероятность отказа в диапазоне [0, 1]."""

        if self._model is not None and self._is_trained_weights_loaded:
            try:
                x = torch.tensor(feature_vector, dtype=torch.float32, device=self._device).unsqueeze(0)
                with torch.no_grad():
                    y = self._model(x)
                return float(y.squeeze().item())
            except Exception as exc:
                raise MLException(
                    message=f"Ошибка инференса predictive-модели: {type(exc).__name__}: {exc}",
                    model_name=self.meta.name,
                ) from exc

        if not self.config.use_heuristic_if_untrained:
            raise MLException(
                message="Весы модели не загружены, эвристический режим отключён",
                model_name=self.meta.name,
            )

        # Эвристический fallback для безопасного запуска до обучения модели.
        return self._heuristic_probability(feature_vector)

    def _heuristic_probability(self, vector: list[float]) -> float:
        """Оценивает риск эвристикой, если обученные веса пока не подключены."""

        # Нормализуем часть признаков, используя устойчивые делители.
        usage_std = self._take(vector, 4)
        zero_growth_ratio = self._take(vector, 10)
        spike_ratio = self._take(vector, 11)
        maintenance_events_90d = self._take(vector, 13)
        downtime_90d = self._take(vector, 15)
        days_since_last_maintenance = self._take(vector, 17)

        score = 0.0
        score += min(1.0, usage_std / 10.0) * 0.20
        score += zero_growth_ratio * 0.15
        score += spike_ratio * 0.20
        score += min(1.0, maintenance_events_90d / 6.0) * 0.15
        score += min(1.0, downtime_90d / 24.0) * 0.15
        score += min(1.0, days_since_last_maintenance / 365.0) * 0.15

        return max(0.0, min(1.0, score))

    def _confidence_level(self, probability: float) -> str:
        """Преобразует вероятность в категорию риска."""

        if probability >= self.config.probability_threshold_high:
            return "high"
        if probability >= self.config.probability_threshold_medium:
            return "medium"
        return "low"

    def _estimate_days_to_failure(self, probability: float) -> int | None:
        """Оценивает горизонт до отказа по вероятности риска."""

        if probability < self.config.probability_threshold_medium:
            return None

        if probability >= self.config.probability_threshold_high:
            return max(7, int(90 * (1.0 - probability)))

        return max(30, int(180 * (1.0 - probability)))

    def _extract_risk_factors_from_dict(
        self,
        payload: dict[str, float] | list[float] | tuple[float, ...],
    ) -> list[str]:
        """Генерирует поясняющие риск-факторы для API и отчётов."""

        if not isinstance(payload, dict):
            return []

        factors: list[str] = []

        usage_std = self._safe_float(payload.get("usage_std", 0.0))
        if usage_std > 5.0:
            factors.append("Высокая волатильность потребления")

        spike_ratio = self._safe_float(payload.get("spike_ratio", 0.0))
        if spike_ratio > 0.2:
            factors.append("Частые пиковые скачки показаний")

        downtime_90d = self._safe_float(payload.get("downtime_hours_90d", 0.0))
        if downtime_90d > 8.0:
            factors.append("Существенный простой оборудования за 90 дней")

        days_since_last = self._safe_float(payload.get("days_since_last_maintenance", 9999.0))
        if days_since_last > 365:
            factors.append("Длительный период без обслуживания")

        return factors

    def _to_feature_vector(self, payload: dict[str, float] | list[float] | tuple[float, ...]) -> list[float]:
        """Приводит payload к плоскому числовому вектору."""

        if isinstance(payload, dict):
            try:
                return [float(payload[key]) for key in sorted(payload.keys())]
            except Exception as exc:
                raise MLException(
                    message=f"Не удалось преобразовать dict признаков: {type(exc).__name__}: {exc}",
                    model_name=self.meta.name,
                ) from exc

        if isinstance(payload, (list, tuple)):
            try:
                return [float(v) for v in payload]
            except Exception as exc:
                raise MLException(
                    message=f"Не удалось преобразовать вектор признаков: {type(exc).__name__}: {exc}",
                    model_name=self.meta.name,
                ) from exc

        raise MLException(
            message=f"Неподдерживаемый тип payload: {type(payload).__name__}",
            model_name=self.meta.name,
        )

    def _resolve_device(self) -> str:
        """Определяет целевое устройство для инференса."""

        if self.config.gpu and torch.cuda.is_available():
            return "cuda:0"
        return "cpu"

    def _validate_config(self) -> None:
        """Проверяет параметры конфигурации модели."""

        cfg = self.config

        if cfg.input_size < 1:
            raise MLException("input_size должен быть >= 1", model_name="failure_forecaster")

        if not cfg.hidden_sizes:
            raise MLException("hidden_sizes не может быть пустым", model_name="failure_forecaster")

        if any(size < 1 for size in cfg.hidden_sizes):
            raise MLException("Размеры hidden слоёв должны быть >= 1", model_name="failure_forecaster")

        if not (0.0 <= cfg.dropout < 1.0):
            raise MLException("dropout должен быть в диапазоне [0, 1)", model_name="failure_forecaster")

        if not (0.0 <= cfg.probability_threshold_medium <= 1.0):
            raise MLException(
                message="probability_threshold_medium должен быть в диапазоне [0, 1]",
                model_name="failure_forecaster",
            )

        if not (0.0 <= cfg.probability_threshold_high <= 1.0):
            raise MLException(
                message="probability_threshold_high должен быть в диапазоне [0, 1]",
                model_name="failure_forecaster",
            )

        if cfg.probability_threshold_medium > cfg.probability_threshold_high:
            raise MLException(
                message="probability_threshold_medium не может быть больше probability_threshold_high",
                model_name="failure_forecaster",
            )

    def _normalize_date(self, value: Any) -> date | None:
        """Нормализует дату в формат date."""

        if value is None:
            return None

        if isinstance(value, date):
            return value

        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            try:
                return date.fromisoformat(value)
            except ValueError:
                return None

        return None

    def _take(self, vector: list[float], idx: int) -> float:
        """Безопасно читает элемент вектора по индексу."""

        if idx < 0 or idx >= len(vector):
            return 0.0
        return float(vector[idx])

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Безопасно приводит значение к float."""

        try:
            return float(value)
        except (TypeError, ValueError):
            return default


class PredictiveForecaster:
    """?????? ????????? ??? ?????????? ????.

    ?????????? ??????????? ??????? ??? ?????????? ????????? ?????.
    """

    def __init__(self) -> None:
        self._version = "heuristic_v1"

    async def predict(self, history: list[dict[str, Any]]) -> dict[str, Any]:
        """??????? ????????????? ??????? ?? ?????? ??????? ????????????."""
        events = len(history)
        probability = min(0.95, 0.1 + events * 0.05)
        confidence = "high" if probability >= 0.7 else "medium" if probability >= 0.4 else "low"
        return {
            "probability": probability,
            "confidence": confidence,
            "predicted_date": None,
            "risk_factors": [f"events_last_period={events}"],
            "model_version": self._version,
        }
