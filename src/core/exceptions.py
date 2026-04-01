# -*- coding: utf-8 -*-
"""
Кастомные исключения приложения
"""

from typing import Any


class AppException(Exception):
    """Базовое исключение приложения"""

    def __init__(
        self,
        message: str = "Ошибка приложения",
        details: Any | None = None,
    ):
        self.message = message
        self.details = details
        super().__init__(self.message)


class NotFoundException(AppException):
    """Ресурс не найден"""

    def __init__(
        self,
        entity: str = "Ресурс",
        entity_id: int | str | None = None,
        message: str | None = None,
    ):
        if message is None:
            if entity_id:
                message = f"{entity} с ID {entity_id} не найден"
            else:
                message = f"{entity} не найден"
        super().__init__(message=message, details={"entity": entity, "entity_id": entity_id})


class ValidationException(AppException):
    """Ошибка валидации данных"""

    def __init__(
        self,
        message: str = "Ошибка валидации",
        field: str | None = None,
        details: Any | None = None,
    ):
        super().__init__(
            message=message,
            details={"field": field, **(details or {})},
        )


class DatabaseException(AppException):
    """Ошибка базы данных"""

    def __init__(
        self,
        message: str = "Ошибка базы данных",
        operation: str | None = None,
    ):
        super().__init__(
            message=message,
            details={"operation": operation},
        )


class MLException(AppException):
    """Ошибка ML-модели"""

    def __init__(
        self,
        message: str = "Ошибка ML-модели",
        model_name: str | None = None,
    ):
        super().__init__(
            message=message,
            details={"model_name": model_name},
        )


class APIException(AppException):
    """Ошибка внешнего API"""

    def __init__(
        self,
        message: str = "Ошибка внешнего API",
        service: str | None = None,
        status_code: int | None = None,
    ):
        super().__init__(
            message=message,
            details={"service": service, "status_code": status_code},
        )


class FileUploadException(AppException):
    """Ошибка загрузки файла"""

    def __init__(
        self,
        message: str = "Ошибка загрузки файла",
        filename: str | None = None,
    ):
        super().__init__(
            message=message,
            details={"filename": filename},
        )
