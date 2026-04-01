# -*- coding: utf-8 -*-
"""
Repository слой — доступ к данным
"""

from src.repositories.base import BaseRepository
from src.repositories.repair_repository import RepairRepository
from src.repositories.meter_repository import MeterRepository
from src.repositories.defect_repository import DefectRepository
from src.repositories.unit_of_work import UnitOfWork

__all__ = [
    "BaseRepository",
    "RepairRepository",
    "MeterRepository",
    "DefectRepository",
    "UnitOfWork",
]
