"""
Модель пользователя
"""

from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel, TimestampMixin


class User(BaseModel, TimestampMixin):
    """
    Пользователь системы.
    
    Роли:
    - admin: полный доступ
    - engineer: доступ к функциям инженера
    - user: базовый доступ
    """

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    full_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        default="user",
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Связи
    repair_requests: Mapped[list["RepairRequest"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )
    inspections: Mapped[list["Inspection"]] = relationship(
        back_populates="inspector",
        lazy="selectin",
    )
    reports: Mapped[list["Report"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"

    @property
    def is_admin(self) -> bool:
        """Проверка на администратора"""
        return self.role == "admin"

    @property
    def is_engineer(self) -> bool:
        """Проверка на инженера"""
        return self.role in ("admin", "engineer")


# Импорты для связей (избегаем циклических импортов)
from src.models.repair import RepairRequest  # noqa: E402
from src.models.defect import Inspection  # noqa: E402
from src.models.report import Report  # noqa: E402
