"""
Парсинг OCR-результата в числовое значение показаний счётчика.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from src.core.exceptions import MLException


@dataclass(slots=True, frozen=True)
class OCRParserConfig:
    """Конфигурация парсера OCR-результата."""

    min_confidence: float = 0.2
    min_digits: int = 3
    max_digits: int = 12
    allow_decimal: bool = True
    decimal_separators: tuple[str, ...] = (".", ",")
    prefer_longest_number: bool = True


@dataclass(slots=True, frozen=True)
class OCRParsedValue:
    """Нормализованный результат парсинга OCR."""

    value: float
    raw_text: str
    confidence: float
    normalized_text: str


class MeterValueParser:
    """Независимый парсер для преобразования OCR-токенов в показание счётчика."""

    _NON_DIGIT_PATTERN = re.compile(r"[^0-9.,]")

    def __init__(self, config: OCRParserConfig | None = None) -> None:
        self.config = config or OCRParserConfig()
        self._validate_config()

    def parse(self, ocr_result: list[dict[str, Any]]) -> OCRParsedValue:
        """
        Извлекает одно итоговое значение счётчика из OCR-результата.

        Алгоритм:
        1) очистка текста токенов
        2) фильтрация по confidence
        3) выбор лучшего кандидата
        4) преобразование в число
        """

        try:
            candidates = self._extract_candidates(ocr_result)
            if not candidates:
                raise MLException(
                    message="Не удалось извлечь числовые кандидаты из OCR-результата",
                    model_name="ocr_parser",
                )

            best_candidate = self._select_best_candidate(candidates)
            parsed_value = self._to_number(best_candidate["normalized_text"])

            return OCRParsedValue(
                value=parsed_value,
                raw_text=best_candidate["raw_text"],
                confidence=best_candidate["confidence"],
                normalized_text=best_candidate["normalized_text"],
            )
        except MLException:
            raise
        except Exception as exc:
            raise MLException(
                message=f"Ошибка парсинга OCR-результата: {type(exc).__name__}: {exc}",
                model_name="ocr_parser",
            ) from exc

    def parse_optional(self, ocr_result: list[dict[str, Any]]) -> OCRParsedValue | None:
        """Мягкий режим: возвращает `None`, если число не удалось распознать."""

        try:
            return self.parse(ocr_result)
        except MLException:
            return None

    def _validate_config(self) -> None:
        """Проверяет корректность конфигурации парсера."""

        cfg = self.config

        if not (0.0 <= cfg.min_confidence <= 1.0):
            raise MLException(
                message="min_confidence должен быть в диапазоне [0, 1]",
                model_name="ocr_parser",
            )

        if cfg.min_digits < 1:
            raise MLException("min_digits должен быть >= 1", model_name="ocr_parser")

        if cfg.max_digits < cfg.min_digits:
            raise MLException(
                message="max_digits должен быть >= min_digits",
                model_name="ocr_parser",
            )

    def _extract_candidates(self, ocr_result: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Формирует список валидных кандидатов на итоговое значение."""

        if not isinstance(ocr_result, list):
            raise MLException(
                message=f"Ожидался list OCR-результатов, получено: {type(ocr_result).__name__}",
                model_name="ocr_parser",
            )

        candidates: list[dict[str, Any]] = []

        for item in ocr_result:
            if not isinstance(item, dict):
                continue

            raw_text = str(item.get("text", "")).strip()
            if not raw_text:
                continue

            confidence = self._safe_confidence(item.get("confidence", 0.0))
            if confidence < self.config.min_confidence:
                continue

            normalized_text = self._normalize_text(raw_text)
            if not normalized_text:
                continue

            digit_count = sum(ch.isdigit() for ch in normalized_text)
            if digit_count < self.config.min_digits or digit_count > self.config.max_digits:
                continue

            candidates.append(
                {
                    "raw_text": raw_text,
                    "normalized_text": normalized_text,
                    "confidence": confidence,
                    "digit_count": digit_count,
                }
            )

        return candidates

    def _select_best_candidate(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        """Выбирает лучший кандидат по длине числа и confidence."""

        if self.config.prefer_longest_number:
            return max(candidates, key=lambda x: (x["digit_count"], x["confidence"]))
        return max(candidates, key=lambda x: (x["confidence"], x["digit_count"]))

    def _normalize_text(self, text: str) -> str:
        """Очищает OCR-текст от шумов и нормализует десятичный разделитель."""

        cleaned = self._NON_DIGIT_PATTERN.sub("", text)
        if not cleaned:
            return ""

        if not self.config.allow_decimal:
            return "".join(ch for ch in cleaned if ch.isdigit())

        # Оставляем только один десятичный разделитель: последний в строке.
        for sep in self.config.decimal_separators:
            cleaned = cleaned.replace(sep, ".")

        if cleaned.count(".") <= 1:
            return cleaned.strip(".")

        last_sep_idx = cleaned.rfind(".")
        integer_part = cleaned[:last_sep_idx].replace(".", "")
        decimal_part = cleaned[last_sep_idx + 1 :].replace(".", "")
        normalized = f"{integer_part}.{decimal_part}" if decimal_part else integer_part
        return normalized.strip(".")

    def _to_number(self, normalized_text: str) -> float:
        """Преобразует нормализованный текст в число."""

        if not normalized_text:
            raise MLException("Пустой нормализованный текст", model_name="ocr_parser")

        # Защита от строк вида '.' или '....'
        if all(ch == "." for ch in normalized_text):
            raise MLException("Некорректный числовой формат", model_name="ocr_parser")

        if "." in normalized_text and self.config.allow_decimal:
            return float(normalized_text)
        return float(int(normalized_text))

    def _safe_confidence(self, value: Any) -> float:
        """Безопасно приводит confidence к float в диапазоне [0, 1]."""

        try:
            confidence = float(value)
        except (TypeError, ValueError):
            confidence = 0.0

        return max(0.0, min(1.0, confidence))
