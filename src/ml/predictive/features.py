# -*- coding: utf-8 -*-
"""
Извлечение признаков для predictive-модели отказов/аномалий.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from statistics import mean, pstdev
from typing import Any

from src.core.exceptions import MLException


@dataclass(slots=True, frozen=True)
class FeatureExtractorConfig:
    """Конфигурация извлечения признаков."""

    lookback_readings: int = 24
    min_readings_required: int = 5
    low_usage_quantile: float = 0.1
    high_usage_quantile: float = 0.9


@dataclass(slots=True, frozen=True)
class FeatureVector:
    """Структурированный набор признаков для модели."""

    feature_names: tuple[str, ...]
    values: tuple[float, ...]
    as_dict: dict[str, float]


class PredictiveFeatureExtractor:
    """Независимый extractor признаков из данных счётчиков и обслуживания."""

    def __init__(self, config: FeatureExtractorConfig | None = None) -> None:
        self.config = config or FeatureExtractorConfig()
        self._validate_config()

    def extract(
        self,
        meter_readings: list[dict[str, Any]],
        maintenance_events: list[dict[str, Any]] | None = None,
        *,
        reference_date: date | datetime | None = None,
    ) -> FeatureVector:
        """
        Собирает признаки для прогноза отказа.

        Входные форматы:
        - meter_readings: [{"reading_value": float|Decimal, "reading_date": date|datetime|ISO str}, ...]
        - maintenance_events: [{"event_date": date|datetime|ISO str, "cost": float, "downtime_hours": float}, ...]
        """

        try:
            normalized_readings = self._normalize_readings(meter_readings)
            if len(normalized_readings) < self.config.min_readings_required:
                raise MLException(
                    message=(
                        "Недостаточно показаний для извлечения признаков: "
                        f"{len(normalized_readings)} < {self.config.min_readings_required}"
                    ),
                    model_name="predictive_features",
                )

            normalized_events = self._normalize_maintenance_events(maintenance_events or [])
            ref_date = self._normalize_date(reference_date) or normalized_readings[-1]["reading_date"]

            values = [item["reading_value"] for item in normalized_readings]
            deltas = self._calc_deltas(values)

            usage_mean = self._safe_mean(deltas)
            usage_std = self._safe_std(deltas)
            usage_min = min(deltas) if deltas else 0.0
            usage_max = max(deltas) if deltas else 0.0
            usage_trend = self._linear_trend(deltas)

            low_q = self._quantile(deltas, self.config.low_usage_quantile)
            high_q = self._quantile(deltas, self.config.high_usage_quantile)

            zero_growth_ratio = self._ratio([d for d in deltas if d <= 0.0], len(deltas))
            spike_ratio = self._ratio([d for d in deltas if d > high_q], len(deltas)) if deltas else 0.0

            last_reading_value = values[-1]
            readings_count = float(len(values))
            days_span = float(max(1, (normalized_readings[-1]["reading_date"] - normalized_readings[0]["reading_date"]).days))

            # Признаки по событиям обслуживания
            events_30d = self._events_in_days(normalized_events, ref_date, 30)
            events_90d = self._events_in_days(normalized_events, ref_date, 90)
            events_365d = self._events_in_days(normalized_events, ref_date, 365)

            downtime_90d = sum(float(event.get("downtime_hours", 0.0)) for event in events_90d)
            maintenance_cost_365d = sum(float(event.get("cost", 0.0)) for event in events_365d)

            days_since_last_maintenance = self._days_since_last_event(normalized_events, ref_date)

            feature_dict: dict[str, float] = {
                "readings_count": readings_count,
                "readings_days_span": days_span,
                "last_reading_value": float(last_reading_value),
                "usage_mean": usage_mean,
                "usage_std": usage_std,
                "usage_min": float(usage_min),
                "usage_max": float(usage_max),
                "usage_trend": usage_trend,
                "usage_low_quantile": low_q,
                "usage_high_quantile": high_q,
                "zero_growth_ratio": zero_growth_ratio,
                "spike_ratio": spike_ratio,
                "maintenance_events_30d": float(len(events_30d)),
                "maintenance_events_90d": float(len(events_90d)),
                "maintenance_events_365d": float(len(events_365d)),
                "downtime_hours_90d": float(downtime_90d),
                "maintenance_cost_365d": float(maintenance_cost_365d),
                "days_since_last_maintenance": float(days_since_last_maintenance),
            }

            names = tuple(feature_dict.keys())
            values_vector = tuple(float(feature_dict[name]) for name in names)

            return FeatureVector(
                feature_names=names,
                values=values_vector,
                as_dict=feature_dict,
            )
        except MLException:
            raise
        except Exception as exc:
            raise MLException(
                message=f"Ошибка извлечения признаков: {type(exc).__name__}: {exc}",
                model_name="predictive_features",
            ) from exc

    def _validate_config(self) -> None:
        """Проверяет конфигурацию extractor-а."""

        cfg = self.config

        if cfg.lookback_readings < 2:
            raise MLException(
                message="lookback_readings должен быть >= 2",
                model_name="predictive_features",
            )

        if cfg.min_readings_required < 2:
            raise MLException(
                message="min_readings_required должен быть >= 2",
                model_name="predictive_features",
            )

        if cfg.min_readings_required > cfg.lookback_readings:
            raise MLException(
                message="min_readings_required не может быть больше lookback_readings",
                model_name="predictive_features",
            )

        if not (0.0 <= cfg.low_usage_quantile < cfg.high_usage_quantile <= 1.0):
            raise MLException(
                message="Квантили должны удовлетворять: 0 <= low < high <= 1",
                model_name="predictive_features",
            )

    def _normalize_readings(self, meter_readings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Нормализует и сортирует показания счётчика."""

        if not isinstance(meter_readings, list):
            raise MLException(
                message=f"Ожидался list показаний, получено: {type(meter_readings).__name__}",
                model_name="predictive_features",
            )

        normalized: list[dict[str, Any]] = []

        for item in meter_readings:
            if not isinstance(item, dict):
                continue

            raw_value = item.get("reading_value")
            raw_date = item.get("reading_date")

            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue

            reading_date = self._normalize_date(raw_date)
            if reading_date is None:
                continue

            normalized.append({"reading_value": value, "reading_date": reading_date})

        normalized.sort(key=lambda x: x["reading_date"])

        if len(normalized) > self.config.lookback_readings:
            normalized = normalized[-self.config.lookback_readings :]

        return normalized

    def _normalize_maintenance_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Нормализует события обслуживания/ремонта."""

        if not isinstance(events, list):
            raise MLException(
                message=f"Ожидался list событий обслуживания, получено: {type(events).__name__}",
                model_name="predictive_features",
            )

        normalized: list[dict[str, Any]] = []

        for event in events:
            if not isinstance(event, dict):
                continue

            event_date = self._normalize_date(event.get("event_date"))
            if event_date is None:
                continue

            cost = self._safe_float(event.get("cost", 0.0))
            downtime_hours = self._safe_float(event.get("downtime_hours", 0.0))

            normalized.append(
                {
                    "event_date": event_date,
                    "cost": max(0.0, cost),
                    "downtime_hours": max(0.0, downtime_hours),
                }
            )

        normalized.sort(key=lambda x: x["event_date"])
        return normalized

    def _calc_deltas(self, values: list[float]) -> list[float]:
        """Вычисляет приращения между соседними показаниями."""

        if len(values) < 2:
            return []
        return [values[i] - values[i - 1] for i in range(1, len(values))]

    def _linear_trend(self, series: list[float]) -> float:
        """Оценивает тренд как наклон линейной регрессии (без внешних библиотек)."""

        n = len(series)
        if n < 2:
            return 0.0

        x_mean = (n - 1) / 2.0
        y_mean = self._safe_mean(series)

        numerator = 0.0
        denominator = 0.0

        for i, value in enumerate(series):
            dx = i - x_mean
            dy = value - y_mean
            numerator += dx * dy
            denominator += dx * dx

        if denominator == 0.0:
            return 0.0

        return numerator / denominator

    def _quantile(self, series: list[float], q: float) -> float:
        """Вычисляет квантиль без numpy/pandas."""

        if not series:
            return 0.0

        sorted_values = sorted(series)
        position = (len(sorted_values) - 1) * q
        left = int(position)
        right = min(left + 1, len(sorted_values) - 1)

        if left == right:
            return float(sorted_values[left])

        weight = position - left
        return float(sorted_values[left] * (1.0 - weight) + sorted_values[right] * weight)

    def _events_in_days(
        self,
        events: list[dict[str, Any]],
        ref_date: date,
        days: int,
    ) -> list[dict[str, Any]]:
        """Фильтрует события за последние N дней."""

        if days < 1:
            return []

        result: list[dict[str, Any]] = []
        for event in events:
            delta_days = (ref_date - event["event_date"]).days
            if 0 <= delta_days <= days:
                result.append(event)
        return result

    def _days_since_last_event(self, events: list[dict[str, Any]], ref_date: date) -> int:
        """Вычисляет дни с последнего события обслуживания."""

        if not events:
            return 9999

        last_date = events[-1]["event_date"]
        delta = (ref_date - last_date).days
        return max(0, delta)

    def _normalize_date(self, value: Any) -> date | None:
        """Преобразует значение к типу date."""

        if value is None:
            return None

        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, date):
            return value

        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None

            # Поддерживаем распространённые форматы дат.
            formats = ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S")
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue

            # Резервный разбор через ISO-формат с таймзоной, если она присутствует.
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
            except ValueError:
                return None

        return None

    def _safe_mean(self, values: list[float]) -> float:
        """Безопасное среднее для пустых списков."""

        if not values:
            return 0.0
        return float(mean(values))

    def _safe_std(self, values: list[float]) -> float:
        """Безопасное стандартное отклонение для коротких списков."""

        if len(values) < 2:
            return 0.0
        return float(pstdev(values))

    def _ratio(self, subset: list[Any], total: int) -> float:
        """Отношение размера подмножества к общему числу элементов."""

        if total <= 0:
            return 0.0
        return float(len(subset) / total)

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Безопасно приводит значение к float."""

        try:
            return float(value)
        except (TypeError, ValueError):
            return default
