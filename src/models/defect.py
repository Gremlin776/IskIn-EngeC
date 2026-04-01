# -*- coding: utf-8 -*-
"""
Модели детекции дефектов конструкций
"""

from datetime import datetime, date
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Date,
    CheckConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel, TimestampMixin


class DefectClass(BaseModel):
    """
    Класс дефекта (трещина, коррозия, деформация и т.д.)
    """

    __tablename__ = "defect_classes"

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
    yolo_class_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    severity_level: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )
    color: Mapped[str] = mapped_column(
        String(7),
        default="#FF0000",
    )

    # Связи
    defects: Mapped[list["DetectedDefect"]] = relationship(
        back_populates="defect_class",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "severity_level BETWEEN 1 AND 5",
            name="check_severity_level",
        ),
    )

    def __repr__(self) -> str:
        return f"<DefectClass(id={self.id}, code='{self.code}')>"


class Inspection(BaseModel, TimestampMixin):
    """
    Обследование конструкций.
    """

    __tablename__ = "inspections"

    inspection_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )
    premise_id: Mapped[int | None] = mapped_column(
        ForeignKey("premises.id"),
        nullable=True,
        index=True,
    )
    building_id: Mapped[int] = mapped_column(
        ForeignKey("buildings.id"),
        nullable=False,
        index=True,
    )
    inspector_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    inspection_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    inspection_type: Mapped[str] = mapped_column(
        String(50),
        default="routine",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="planned",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Связи
    premise: Mapped["Premise | None"] = relationship(
        back_populates="inspections",
    )
    building: Mapped["Building"] = relationship(
        back_populates="inspections",
    )
    inspector: Mapped["User"] = relationship(
        back_populates="inspections",
    )
    photos: Mapped[list["InspectionPhoto"]] = relationship(
        back_populates="inspection",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    defects: Mapped[list["DetectedDefect"]] = relationship(
        back_populates="inspection",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Inspection(id={self.id}, number='{self.inspection_number}')>"


class InspectionPhoto(BaseModel):
    """
    Фотография обследования.
    """

    __tablename__ = "inspection_photos"

    inspection_id: Mapped[int] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"),
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
    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    location_desc: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    taken_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        server_default=func.now(),
    )

    # Связи
    inspection: Mapped["Inspection"] = relationship(
        back_populates="photos",
    )
    defects: Mapped[list["DetectedDefect"]] = relationship(
        back_populates="photo",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<InspectionPhoto(id={self.id}, file_name='{self.file_name}')>"


class DetectedDefect(BaseModel, TimestampMixin):
    """
    Детектированный дефект на фотографии.
    """

    __tablename__ = "detected_defects"

    inspection_id: Mapped[int] = mapped_column(
        ForeignKey("inspections.id"),
        nullable=False,
        index=True,
    )
    photo_id: Mapped[int] = mapped_column(
        ForeignKey("inspection_photos.id"),
        nullable=False,
        index=True,
    )
    defect_class_id: Mapped[int] = mapped_column(
        ForeignKey("defect_classes.id"),
        nullable=False,
        index=True,
    )
    confidence: Mapped[float] = mapped_column(
        nullable=False,
    )
    bbox_x: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    bbox_y: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    bbox_width: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    bbox_height: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    severity: Mapped[str] = mapped_column(
        String(10),
        default="medium",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="detected",
        index=True,
    )
    review_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    # Связи
    inspection: Mapped["Inspection"] = relationship(
        back_populates="defects",
    )
    photo: Mapped["InspectionPhoto"] = relationship(
        back_populates="defects",
    )
    defect_class: Mapped["DefectClass"] = relationship(
        back_populates="defects",
    )
    reviewer: Mapped["User | None"] = relationship(
        back_populates="reviewed_defects",
    )

    def __repr__(self) -> str:
        return f"<DetectedDefect(id={self.id}, class_id={self.defect_class_id})>"


# Импорты для связей
from src.models.building import Building, Premise  # noqa: E402
from src.models.user import User  # noqa: E402
