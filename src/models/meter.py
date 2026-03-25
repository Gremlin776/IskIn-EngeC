"""
Модели учёта счётчиков
"""

from decimal import Decimal
from datetime import datetime, date
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    Date,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel, TimestampMixin


class MeterType(BaseModel):
    """
    Тип счётчика (вода, электричество, газ и т.д.)
    """

    __tablename__ = "meter_types"

    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )
    unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    icon: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Связи
    meters: Mapped[list["Meter"]] = relationship(
        back_populates="meter_type",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<MeterType(id={self.id}, code='{self.code}')>"


class Meter(BaseModel, TimestampMixin):
    """
    Счётчик ресурсов.
    """

    __tablename__ = "meters"

    meter_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    premise_id: Mapped[int] = mapped_column(
        ForeignKey("premises.id"),
        nullable=False,
        index=True,
    )
    meter_type_id: Mapped[int] = mapped_column(
        ForeignKey("meter_types.id"),
        nullable=False,
        index=True,
    )
    manufacturer: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    serial_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    install_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    verification_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    next_verification: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    # Связи
    premise: Mapped["Premise"] = relationship(
        back_populates="meters",
    )
    meter_type: Mapped["MeterType"] = relationship(
        back_populates="meters",
    )
    readings: Mapped[list["MeterReading"]] = relationship(
        back_populates="meter",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Meter(id={self.id}, number='{self.meter_number}')>"


class MeterReading(BaseModel):
    """
    Показание счётчика.
    """

    __tablename__ = "meter_readings"

    meter_id: Mapped[int] = mapped_column(
        ForeignKey("meters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reading_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
    )
    reading_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    photo_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    ocr_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    verified_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    source: Mapped[str] = mapped_column(
        String(20),
        default="manual",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default="now()",
    )

    # Связи
    meter: Mapped["Meter"] = relationship(
        back_populates="readings",
    )
    verifier: Mapped["User | None"] = relationship(
        back_populates="verified_readings",
    )

    __table_args__ = (
        UniqueConstraint("meter_id", "reading_date"),
    )

    def __repr__(self) -> str:
        return f"<MeterReading(id={self.id}, value={self.reading_value})>"


class OCRProcessingLog(BaseModel):
    """
    Лог обработки OCR.
    """

    __tablename__ = "ocr_processing_log"

    original_image: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    processed_image: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    ocr_raw_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    parsed_value: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4),
        nullable=True,
    )
    confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )
    processing_time_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="success",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default="now()",
    )

    def __repr__(self) -> str:
        return f"<OCRProcessingLog(id={self.id}, status='{self.status}')>"


# Импорты для связей
from src.models.building import Premise  # noqa: E402
from src.models.user import User  # noqa: E402

# Добавляем связь в модель User
User.verified_readings = relationship(  # type: ignore[attr-defined]
    "MeterReading",
    foreign_keys="MeterReading.verified_by",
    lazy="selectin",
)
