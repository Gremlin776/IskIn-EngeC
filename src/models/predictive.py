"""
Модели предиктивного обслуживания
"""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Date,
    Numeric,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel, TimestampMixin


class FailurePrediction(BaseModel, TimestampMixin):
    """
    Прогноз поломки оборудования.
    """

    __tablename__ = "failure_predictions"

    premise_id: Mapped[int | None] = mapped_column(
        ForeignKey("premises.id"),
        nullable=True,
        index=True,
    )
    meter_id: Mapped[int | None] = mapped_column(
        ForeignKey("meters.id"),
        nullable=True,
        index=True,
    )
    equipment_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    prediction_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    failure_probability: Mapped[float] = mapped_column(
        nullable=False,
    )
    predicted_failure_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    confidence_level: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    risk_factors: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    recommendations: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    model_version: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    is_actual: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
    )

    # Связи
    premise: Mapped["Premise | None"] = relationship(
        back_populates="predictions",
    )
    meter: Mapped["Meter | None"] = relationship(
        back_populates="predictions",
    )

    def __repr__(self) -> str:
        return f"<FailurePrediction(id={self.id}, probability={self.failure_probability})>"


class MaintenanceHistory(BaseModel, TimestampMixin):
    """
    История событий обслуживания для обучения моделей.
    """

    __tablename__ = "maintenance_history"

    entity_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    event_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    cost: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    downtime_hours: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<MaintenanceHistory(id={self.id}, event_type='{self.event_type}')>"


# Импорты для связей
from src.models.building import Premise  # noqa: E402
from src.models.meter import Meter  # noqa: E402

# Добавляем связи в модели
Premise.predictions = relationship(  # type: ignore[attr-defined]
    "FailurePrediction",
    back_populates="premise",
    lazy="selectin",
)

Meter.predictions = relationship(  # type: ignore[attr-defined]
    "FailurePrediction",
    back_populates="meter",
    lazy="selectin",
)
