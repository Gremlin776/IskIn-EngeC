# -*- coding: utf-8 -*-
"""
Настройка логирования
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

from src.core.config import get_settings

settings = get_settings()


def setup_logging() -> None:
    """
    Настройка системы логирования.
    
    Создаёт:
    - Консольный обработчик (stdout)
    - Файловый обработчик с ротацией
    """
    # Создаём директорию для логов
    log_path = settings.log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Конфигурация формата
    log_format = logging.Formatter(
        fmt=(
            "%(asctime)s | %(levelname)-8s | "
            "%(name)s:%(lineno)d | %(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)

    # Файловый обработчик с ротацией
    file_handler = RotatingFileHandler(
        filename=log_path,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Получение логгера по имени.
    
    Args:
        name: Имя логгера (обычно __name__ модуля)
    
    Returns:
        Настроенный логгер
    """
    return logging.getLogger(name)
