# -*- coding: utf-8 -*-
"""
NLP модуль для обработки текстовой документации в строительстве.

Включает:
- psd_comparator: Сравнение проектно-сметной документации (ПСД)
- repair_classifier: Классификация типов ремонтов
"""

from src.ml.nlp.psd_comparator import PSDComparator
from src.ml.nlp.repair_classifier import RepairClassifier

__all__ = [
    "PSDComparator",
    "RepairClassifier",
]
