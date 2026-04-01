# -*- coding: utf-8 -*-
"""
Классы дефектов для YOLO-модели детекции.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from src.core.exceptions import MLException


class DefectClass(IntEnum):
    """Индексы классов дефектов в датасете YOLO."""

    CRACK = 0
    LEAK = 1
    CORROSION = 2
    MOLD = 3
    ELECTRICAL_DAMAGE = 4
    PAINT_PEELING = 5
    RUST_STAIN = 6
    OTHER_DAMAGE = 7


@dataclass(slots=True, frozen=True)
class DefectClassInfo:
    """Метаданные класса дефекта."""

    class_id: int
    code: str
    name_ru: str
    description_ru: str
    severity_default: int


# Единый справочник классов дефектов.
DEFECT_CLASS_MAP: dict[int, DefectClassInfo] = {
    DefectClass.CRACK.value: DefectClassInfo(
        class_id=DefectClass.CRACK.value,
        code="crack",
        name_ru="Трещина",
        description_ru="Трещины в стенах, перекрытиях, плитке и других конструкциях.",
        severity_default=4,
    ),
    DefectClass.LEAK.value: DefectClassInfo(
        class_id=DefectClass.LEAK.value,
        code="leak",
        name_ru="Протечка",
        description_ru="Следы активной или недавней протечки воды.",
        severity_default=5,
    ),
    DefectClass.CORROSION.value: DefectClassInfo(
        class_id=DefectClass.CORROSION.value,
        code="corrosion",
        name_ru="Коррозия",
        description_ru="Коррозионные повреждения металлических элементов.",
        severity_default=3,
    ),
    DefectClass.MOLD.value: DefectClassInfo(
        class_id=DefectClass.MOLD.value,
        code="mold",
        name_ru="Плесень",
        description_ru="Очаги плесени и биопоражения поверхностей.",
        severity_default=4,
    ),
    DefectClass.ELECTRICAL_DAMAGE.value: DefectClassInfo(
        class_id=DefectClass.ELECTRICAL_DAMAGE.value,
        code="electrical_damage",
        name_ru="Повреждение электрики",
        description_ru="Повреждения электрических узлов, розеток, кабелей или щитов.",
        severity_default=5,
    ),
    DefectClass.PAINT_PEELING.value: DefectClassInfo(
        class_id=DefectClass.PAINT_PEELING.value,
        code="paint_peeling",
        name_ru="Отслоение покрытия",
        description_ru="Отслоение краски, штукатурки или декоративного слоя.",
        severity_default=2,
    ),
    DefectClass.RUST_STAIN.value: DefectClassInfo(
        class_id=DefectClass.RUST_STAIN.value,
        code="rust_stain",
        name_ru="Ржавый подтёк",
        description_ru="Подтёки ржавчины и локальные следы окисления.",
        severity_default=2,
    ),
    DefectClass.OTHER_DAMAGE.value: DefectClassInfo(
        class_id=DefectClass.OTHER_DAMAGE.value,
        code="other_damage",
        name_ru="Иное повреждение",
        description_ru="Прочие визуальные повреждения, не попавшие в отдельные классы.",
        severity_default=2,
    ),
}

# Индексы для быстрого поиска по коду класса.
DEFECT_CLASS_BY_CODE: dict[str, DefectClassInfo] = {
    info.code: info for info in DEFECT_CLASS_MAP.values()
}


def get_defect_class_info(class_id: int) -> DefectClassInfo:
    """Возвращает информацию о классе дефекта по его числовому ID."""

    info = DEFECT_CLASS_MAP.get(class_id)
    if info is None:
        raise MLException(
            message=f"Неизвестный class_id дефекта: {class_id}",
            model_name="yolo_detection_classes",
        )
    return info


def get_defect_class_info_by_code(code: str) -> DefectClassInfo:
    """Возвращает информацию о классе дефекта по строковому коду."""

    normalized = code.strip().lower()
    if not normalized:
        raise MLException(
            message="Код класса дефекта не может быть пустым",
            model_name="yolo_detection_classes",
        )

    info = DEFECT_CLASS_BY_CODE.get(normalized)
    if info is None:
        raise MLException(
            message=f"Неизвестный код класса дефекта: {code}",
            model_name="yolo_detection_classes",
        )
    return info


def get_yolo_names_mapping() -> dict[int, str]:
    """Отдаёт словарь имён классов для конфигурации/проверки YOLO."""

    return {class_id: info.code for class_id, info in DEFECT_CLASS_MAP.items()}
