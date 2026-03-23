"""
Модели журнала ремонтных работ
"""

from decimal import Decimal
from datetime import date
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Numeric,
    Date,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel, TimestampMixin


class RepairType(BaseModel):
    """
    Тип ремонтной работы.
    """

    __tablename__ = "repair_types"

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )

    # Связи
    repair_requests: Mapped[list["RepairRequest"]] = relationship(
        back_populates="repair_type",
    )

    def __repr__(self) -> str:
        return f"<RepairType(id={self.id}, code='{self.code}')>"


class RepairRequest(BaseModel, TimestampMixin):
    """
    Заявка на ремонт.
    
    Статусы:
    - new: новая заявка
    - in_progress: в работе
    - completed: завершена
    - cancelled: отменена
    
    Приоритеты:
    - low: низкий
    - medium: средний
    - high: высокий
    - critical: критический
    """

    __tablename__ = "repair_requests"

    request_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )
    premise_id: Mapped[int] = mapped_column(
        ForeignKey("premises.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    repair_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("repair_types.id"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="new",
        nullable=False,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(10),
        default="medium",
        nullable=False,
    )
    scheduled_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    completed_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    cost: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Связи
    premise: Mapped["Premise"] = relationship(
        back_populates="repair_requests",
    )
    user: Mapped["User"] = relationship(
        back_populates="repair_requests",
    )
    repair_type: Mapped["RepairType | None"] = relationship(
        back_populates="repair_requests",
    )
    photos: Mapped[list["RepairPhoto"]] = relationship(
        back_populates="repair_request",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    comments: Mapped[list["RepairComment"]] = relationship(
        back_populates="repair_request",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<RepairRequest(id={self.id}, number='{self.request_number}')>"


class RepairPhoto(BaseModel):
    """
    Фотография к заявке на ремонт.
    """

    __tablename__ = "repair_photos"

    repair_request_id: Mapped[int] = mapped_column(
        ForeignKey("repair_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_size: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    mime_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    is_main: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    uploaded_at: Mapped[DateTime] = mapped_column(
        default="now()",
    )

    # Связи
    repair_request: Mapped["RepairRequest"] = relationship(
        back_populates="photos",
    )

    def __repr__(self) -> str:
        return f"<RepairPhoto(id={self.id}, file_name='{self.file_name}')>"


class RepairComment(BaseModel, TimestampMixin):
    """
    Комментарий к заявке на ремонт.
    """

    __tablename__ = "repair_comments"

    repair_request_id: Mapped[int] = mapped_column(
        ForeignKey("repair_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    comment_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Связи
    repair_request: Mapped["RepairRequest"] = relationship(
        back_populates="comments",
    )
    user: Mapped["User"] = relationship(
        back_populates="comments",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<RepairComment(id={self.id}, request_id={self.repair_request_id})>"


# Импорты для связей
from src.models.building import Premise  # noqa: E402
from src.models.user import User  # noqa: E402
