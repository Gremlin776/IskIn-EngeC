"""
Базовые классы для ORM моделей
"""

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""

    pass


class BaseModel(Base):
    """
    Базовая модель с первичным ключом.
    
    Наследуется от DeclarativeBase.
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )


class TimestampMixin:
    """
    Миксин для добавления полей created_at и updated_at.
    
    Использование:
        class MyModel(BaseModel, TimestampMixin):
            __tablename__ = "my_table"
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
