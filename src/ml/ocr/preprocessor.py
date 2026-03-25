"""
Предобработка изображений счётчиков перед OCR.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from src.core.exceptions import MLException


@dataclass(slots=True, frozen=True)
class OCRPreprocessConfig:
    """Конфигурация пайплайна предобработки изображения счётчика."""

    target_width: int = 1024
    denoise_kernel: int = 3
    clahe_clip_limit: float = 2.5
    clahe_grid_size: int = 8
    adaptive_block_size: int = 31
    adaptive_c: int = 10
    morph_kernel_size: int = 3
    deskew: bool = True


class MeterImagePreprocessor:
    """Независимый preprocessor для OCR распознавания показаний счётчика."""

    def __init__(self, config: OCRPreprocessConfig | None = None) -> None:
        self.config = config or OCRPreprocessConfig()
        self._validate_config()

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Запускает полный пайплайн предобработки.

        Возвращает бинаризованное выровненное изображение, оптимизированное для OCR.
        """

        try:
            prepared = self._validate_and_normalize_image(image)
            resized = self._resize_to_target(prepared)
            denoised = self._denoise(resized)
            gray = self._to_grayscale(denoised)
            contrast = self._enhance_contrast(gray)
            binary = self._binarize(contrast)
            cleaned = self._cleanup(binary)
            if self.config.deskew:
                return self._deskew(cleaned)
            return cleaned
        except MLException:
            raise
        except Exception as exc:
            raise MLException(
                message=f"Ошибка предобработки изображения счётчика: {type(exc).__name__}: {exc}",
                model_name="ocr_preprocessor",
            ) from exc

    def preprocess_from_path(self, image_path: str | Path) -> np.ndarray:
        """Читает изображение с диска и запускает предобработку."""

        try:
            path = Path(image_path)
            if not path.exists() or not path.is_file():
                raise MLException(
                    message=f"Файл изображения не найден: {path}",
                    model_name="ocr_preprocessor",
                )

            image = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if image is None:
                raise MLException(
                    message=f"Не удалось прочитать изображение: {path}",
                    model_name="ocr_preprocessor",
                )
            return self.preprocess(image)
        except MLException:
            raise
        except Exception as exc:
            raise MLException(
                message=f"Ошибка чтения изображения с диска: {type(exc).__name__}: {exc}",
                model_name="ocr_preprocessor",
            ) from exc

    def preprocess_from_bytes(self, payload: bytes) -> np.ndarray:
        """Декодирует изображение из bytes и запускает предобработку."""

        try:
            if not payload:
                raise MLException(
                    message="Пустой бинарный payload изображения",
                    model_name="ocr_preprocessor",
                )

            np_buffer = np.frombuffer(payload, dtype=np.uint8)
            image = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
            if image is None:
                raise MLException(
                    message="Не удалось декодировать изображение из bytes",
                    model_name="ocr_preprocessor",
                )
            return self.preprocess(image)
        except MLException:
            raise
        except Exception as exc:
            raise MLException(
                message=f"Ошибка декодирования изображения: {type(exc).__name__}: {exc}",
                model_name="ocr_preprocessor",
            ) from exc

    def _validate_config(self) -> None:
        """Проверяет конфигурацию, чтобы избежать ошибок OpenCV на рантайме."""

        cfg = self.config

        if cfg.target_width < 64:
            raise MLException("target_width должен быть >= 64", model_name="ocr_preprocessor")

        if cfg.denoise_kernel < 1 or cfg.denoise_kernel % 2 == 0:
            raise MLException(
                "denoise_kernel должен быть нечётным и >= 1",
                model_name="ocr_preprocessor",
            )

        if cfg.adaptive_block_size < 3 or cfg.adaptive_block_size % 2 == 0:
            raise MLException(
                "adaptive_block_size должен быть нечётным и >= 3",
                model_name="ocr_preprocessor",
            )

        if cfg.morph_kernel_size < 1:
            raise MLException(
                "morph_kernel_size должен быть >= 1",
                model_name="ocr_preprocessor",
            )

    def _validate_and_normalize_image(self, image: np.ndarray) -> np.ndarray:
        """Проверяет тип/формат входного изображения и нормализует его."""

        if not isinstance(image, np.ndarray):
            raise MLException(
                message=f"Ожидался np.ndarray, получено: {type(image).__name__}",
                model_name="ocr_preprocessor",
            )

        if image.size == 0:
            raise MLException("Передано пустое изображение", model_name="ocr_preprocessor")

        if image.ndim == 2:
            return image

        if image.ndim == 3 and image.shape[2] in (3, 4):
            if image.shape[2] == 4:
                return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
            return image

        raise MLException(
            message=f"Неподдерживаемая форма изображения: {image.shape}",
            model_name="ocr_preprocessor",
        )

    def _resize_to_target(self, image: np.ndarray) -> np.ndarray:
        """Масштабирует изображение до целевой ширины с сохранением пропорций."""

        height, width = image.shape[:2]
        if width <= 0 or height <= 0:
            raise MLException("Некорректный размер изображения", model_name="ocr_preprocessor")

        if width == self.config.target_width:
            return image

        scale = self.config.target_width / float(width)
        new_height = max(1, int(height * scale))
        interpolation = cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA
        return cv2.resize(image, (self.config.target_width, new_height), interpolation=interpolation)

    def _denoise(self, image: np.ndarray) -> np.ndarray:
        """Подавляет шумы, сохраняя границы цифр."""

        ksize = self.config.denoise_kernel
        return cv2.GaussianBlur(image, (ksize, ksize), 0)

    def _to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """Переводит изображение в градации серого."""

        if image.ndim == 2:
            return image
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def _enhance_contrast(self, gray: np.ndarray) -> np.ndarray:
        """Локально повышает контраст для более стабильного OCR."""

        clahe = cv2.createCLAHE(
            clipLimit=self.config.clahe_clip_limit,
            tileGridSize=(self.config.clahe_grid_size, self.config.clahe_grid_size),
        )
        return clahe.apply(gray)

    def _binarize(self, image: np.ndarray) -> np.ndarray:
        """Бинаризация адаптивным порогом для неравномерного освещения."""

        return cv2.adaptiveThreshold(
            image,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            self.config.adaptive_block_size,
            self.config.adaptive_c,
        )

    def _cleanup(self, image: np.ndarray) -> np.ndarray:
        """Убирает мелкие артефакты морфологической обработкой."""

        kernel = np.ones((self.config.morph_kernel_size, self.config.morph_kernel_size), dtype=np.uint8)
        opened = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
        return closed

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """Пытается выровнять наклон табло по доминирующему углу текста."""

        try:
            points = np.column_stack(np.where(image < 128))
            if len(points) < 20:
                return image

            rect = cv2.minAreaRect(points.astype(np.float32))
            angle = rect[-1]

            # OpenCV возвращает угол в диапазоне [-90, 0); приводим к удобному виду.
            if angle < -45:
                angle = 90 + angle

            if abs(angle) < 0.3:
                return image

            h, w = image.shape[:2]
            center = (w // 2, h // 2)
            matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            return cv2.warpAffine(
                image,
                matrix,
                (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )
        except Exception:
            # Если deskew не удался, возвращаем исходный кадр без падения пайплайна.
            return image
