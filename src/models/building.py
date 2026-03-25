"""
Модели зданий и помещений
"""

from decimal import Decimal
from datetime import datetime, date
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel, TimestampMixin


class Building(BaseModel, TimestampMixin):
    """
    Здание/объект эксплуатации.
    """

    __tablename__ = "buildings"

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    address: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    building_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    year_built: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    floors: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    total_area: Mapped[Decimal | None] = mapped_column(
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    # Связи
    premises: Mapped[list["Premise"]] = relationship(
        back_populates="building",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    inspections: Mapped[list["Inspection"]] = relationship(
        back_populates="building",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Building(id={self.id}, name='{self.name}')>"


class Premise(BaseModel, TimestampMixin):
    """
    Помещение в здании.
    """

    __tablename__ = "premises"

    building_id: Mapped[int] = mapped_column(
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    floor: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    room_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    room_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    room_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    area: Mapped[Decimal | None] = mapped_column(
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    # Связи
    building: Mapped["Building"] = relationship(
        back_populates="premises",
    )
    repair_requests: Mapped[list["RepairRequest"]] = relationship(
        back_populates="premise",
        lazy="selectin",
    )
    meters: Mapped[list["Meter"]] = relationship(
        back_populates="premise",
        lazy="selectin",
    )
    inspections: Mapped[list["Inspection"]] = relationship(
        back_populates="premise",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("building_id", "floor", "room_number"),
    )

    def __repr__(self) -> str:
        return f"<Premise(id={self.id}, room_number='{self.room_number}')>"


# Импорты для связей
from src.models.defect import Inspection  # noqa: E402
from src.models.repair import RepairRequest  # noqa: E402
from src.models.meter import Meter  # noqa: E402
