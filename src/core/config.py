"""
Конфигурация приложения
"""

from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # Игнорировать переменные окружения системы, использовать только .env
        env_prefix="ISKIN_",
    )

    # ============================================
    # ПРИЛОЖЕНИЕ
    # ============================================
    app_name: str = "Инженерный ИскИн"
    app_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"

    # ============================================
    # БАЗА ДАННЫХ
    # ============================================
    database_url: str = "sqlite+aiosqlite:///./iskin.db"

    # ============================================
    # БЕЗОПАСНОСТЬ
    # ============================================
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # ============================================
    # ФАЙЛЫ
    # ============================================
    upload_dir: str = "./uploads"
    max_upload_size: int = 10 * 1024 * 1024  # 10 MB

    # ============================================
    # ML МОДЕЛИ
    # ============================================
    yolo_model_path: str = "./models/yolo/best.pt"
    ocr_langs: str = "ru,en"
    ocr_gpu: bool = True

    # ============================================
    # LLM API
    # ============================================
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"

    # ============================================
    # ЛОГИРОВАНИЕ
    # ============================================
    log_level: str = "INFO"
    log_file: str = "./logs/iskin.log"

    # ============================================
    # Свойства
    # ============================================
    @property
    def ocr_languages(self) -> list[str]:
        """Список языков для OCR"""
        return [lang.strip() for lang in self.ocr_langs.split(",")]

    @property
    def upload_path(self) -> Path:
        """Путь к директории загрузок"""
        return Path(self.upload_dir).resolve()

    @property
    def log_path(self) -> Path:
        """Путь к файлу логов"""
        return Path(self.log_file).resolve()

    @property
    def is_production(self) -> bool:
        """Режим продакшена"""
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Получение настроек (кэшируется)"""
    return Settings()
