# -*- coding: utf-8 -*-
"""
Модели генерации отчётов
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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel, TimestampMixin


class ReportTemplate(BaseModel, TimestampMixin):
    """
    Шаблон отчёта.
    """

    __tablename__ = "report_templates"

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
    template_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    # Связи
    reports: Mapped[list["Report"]] = relationship(
        back_populates="template",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ReportTemplate(id={self.id}, code='{self.code}')>"


class Report(BaseModel, TimestampMixin):
    """
    Отчёт.
    """

    __tablename__ = "reports"

    report_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("report_templates.id"),
        nullable=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    report_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    period_start: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    period_end: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    llm_model_used: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    llm_tokens_used: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    file_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
    )

    # Связи
    template: Mapped["ReportTemplate | None"] = relationship(
        back_populates="reports",
    )
    user: Mapped["User"] = relationship(
        back_populates="reports",
    )
    entities: Mapped[list["ReportEntity"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Report(id={self.id}, number='{self.report_number}')>"


class ReportEntity(BaseModel):
    """
    Связь отчёта с объектами (заявки, обследования и т.д.)
    """

    __tablename__ = "report_entities"

    report_id: Mapped[int] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    entity_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Связи
    report: Mapped["Report"] = relationship(
        back_populates="entities",
    )

    def __repr__(self) -> str:
        return f"<ReportEntity(report_id={self.report_id}, entity_type='{self.entity_type}')>"


# Импорты для связей
from src.models.user import User  # noqa: E402
