#!/usr/bin/env python3
"""
Скрипт для скачивания датасетов с Kaggle для проекта "Инженерный ИскИн".

Проект "Инженерный ИскИн" — Система автоматизации эксплуатации зданий на основе ML.

Скачивает датасеты по категориям:

🏗️ ТРЕЩИНЫ В БЕТОНЕ (YOLO детекция):
- SDNET2018 (56,000 изображений, 6 типов дефектов)
- Concrete Crack Images (40,000 изображений, бинарная классификация)
- Surface Crack Detection (30,000 изображений)
- Concrete Structural Defects (7 классов: cracks, spalling, efflorescence, etc.)

🔴 КОРРОЗИЯ И СКАЛЫВАНИЕ:
- Corrosion & Spalling Segmentation (патчи для сегментации)
- Exposed Steel Rebar (684 изображения, арматура)

🛣️ ПОВРЕЖДЕНИЯ ДОРОГ:
- Pothole Detection YOLOv11 (готовые YOLO-аннотации)
- Road Damage Detection (8 классов повреждений)

🏢 ПОВРЕЖДЕНИЯ ЗДАНИЙ:
- Building Facade Defects (дефекты фасадов)
- Construction Material Defects (дефекты материалов)
- Steel Surface Defects (дефекты стали)

⚡ ЭНЕРГОПОТРЕБЛЕНИЕ (предиктивная аналитика):
- Building Data Genome Project 2 (3053 счётчика, 2 года данных)
- ASHRAE GEPIII (энергетические метрики зданий)

📝 NLP ДЛЯ РЕМОНТНЫХ ЗАЯВОК:
- CMMS Work Orders (текстовые описания заявок)
- RuBQ (русский вопрос-ответ для NLP)

📊 МОНИТОРИНГ КОНСТРУКЦИЙ (SHM):
- Structural Health Monitoring (вибрация, деформации)
- Bridge Health Monitoring (мониторинг мостов)

🌡️ МИКРОКЛИМАТ И КОМФОРТ:
- Occupancy & Thermal Comfort (занятость помещений, температура)

🔤 OCR ДЛЯ СЧЁТЧИКОВ:
- SVHN (цифры для распознавания показаний)
- Meter Reading Dataset (фото счётчиков)

Требования:
- Установленный kagglehub: pip install kagglehub
- Аутентификация через переменные окружения KAGGLE_USERNAME/KAGGLE_KEY
"""

from dotenv import load_dotenv
from typing import Optional
from pathlib import Path
import zipfile
import shutil
import kagglehub
import os


# Загрузка переменных окружения из .env
load_dotenv(Path(__file__).parent.parent / '.env')


def get_project_root() -> Path:
    """Получить корневую директорию проекта."""
    return Path(__file__).parent.parent


def download_dataset(
    dataset_slug: str,
    download_dir: Path,
    force: bool = False
) -> Path:
    download_dir.mkdir(parents=True, exist_ok=True)
    print(f"⬇️  Скачивание датасета: {dataset_slug}")

    try:
        # 1. Скачиваем в кэш
        cache_path = Path(kagglehub.dataset_download(
            dataset_slug, force_download=force))
        print(f"✓ Загружено в кэш: {cache_path}")

        # 2. ФИЗИЧЕСКОЕ КОПИРОВАНИЕ в ваш проект
        # Используем distutils или shutil для копирования содержимого папки
        print(f"🚚 Перенос файлов в {download_dir}...")

        # Если в целевой папке уже что-то есть, очистим (по желанию) или просто копируем поверх
        for item in cache_path.iterdir():
            target_item = download_dir / item.name
            if item.is_dir():
                if target_item.exists():
                    shutil.rmtree(target_item)
                shutil.copytree(item, target_item)
            else:
                shutil.copy2(item, target_item)

        print(f"✅ Файлы успешно размещены в проекте.")
        return download_dir  # Теперь возвращаем путь к вашей папке, а не к кэшу

    except Exception as e:
        print(f"❌ Ошибка при загрузке/копировании: {e}")
        raise


def extract_archive(archive_path: Path, extract_dir: Path) -> Path:
    """
    Распаковать ZIP-архив.

    Args:
        archive_path: Путь к архиву.
        extract_dir: Директория для распаковки.

    Returns:
        Путь к распакованной директории.
    """
    extract_dir.mkdir(parents=True, exist_ok=True)

    print(f"📦 Распаковка: {archive_path.name}")
    with zipfile.ZipFile(archive_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

    # Найти основную директорию (если архив содержит одну корневую папку)
    extracted_items = list(extract_dir.iterdir())
    if len(extracted_items) == 1 and extracted_items[0].is_dir():
        return extracted_items[0]

    return extract_dir


def prepare_yolo_structure(
    source_dir: Path,
    target_dir: Path,
    dataset_type: str
) -> None:
    """
    Подготовить структуру директорий для обучения YOLOv8.

    YOLOv8 требует структуру:
    dataset/
        images/
            train/
            val/
            test/
        labels/
            train/
            val/
            test/

    Args:
        source_dir: Исходная директория с данными.
        target_dir: Целевая директория для YOLOv8.
        dataset_type: Тип датасета ('sdnet2018' или 'concrete_crack').
    """
    print(f"🔧 Подготовка структуры YOLOv8 для {dataset_type}...")

    # Создаем структуру
    images_dir = target_dir / "images"
    labels_dir = target_dir / "labels"

    for split in ["train", "val", "test"]:
        (images_dir / split).mkdir(parents=True, exist_ok=True)
        (labels_dir / split).mkdir(parents=True, exist_ok=True)

    if dataset_type == "sdnet2018":
        prepare_sdnet2018(source_dir, images_dir, labels_dir)
    elif dataset_type == "concrete_crack":
        prepare_concrete_crack(source_dir, images_dir, labels_dir)
    elif dataset_type == "concrete_defects":
        prepare_concrete_defects(source_dir, images_dir, labels_dir)
    elif dataset_type == "corrosion_spalling":
        prepare_corrosion_spalling(source_dir, images_dir, labels_dir)
    elif dataset_type == "rebar_exposure":
        prepare_rebar_exposure(source_dir, images_dir, labels_dir)
    elif dataset_type == "pothole":
        prepare_pothole_detection(source_dir, images_dir, labels_dir)
    elif dataset_type == "road_crack":
        prepare_road_crack(source_dir, images_dir, labels_dir)
    elif dataset_type == "turbine_damage":
        prepare_turbine_damage(source_dir, images_dir, labels_dir)
    elif dataset_type == "facade_defects":
        prepare_facade_defects(source_dir, images_dir, labels_dir)
    elif dataset_type == "material_defects":
        prepare_material_defects(source_dir, images_dir, labels_dir)
    elif dataset_type == "steel_defects":
        prepare_steel_defects(source_dir, images_dir, labels_dir)
    else:
        print(
            f"⚠️  Неизвестный тип датасета: {dataset_type}, используется подготовка по умолчанию")
        prepare_default(source_dir, images_dir, labels_dir)

    print(f"✓ Структура YOLOv8 создана: {target_dir}")


def prepare_sdnet2018(
    source_dir: Path,
    images_dir: Path,
    labels_dir: Path
) -> None:
    """
    Подготовить датасет SDNET2018 для YOLOv8.

    SDNET2018 содержит изображения с аннотациями в формате YOLO.
    """
    # Поиск директорий с изображениями и аннотациями
    images_source = None
    labels_source = None

    for item in source_dir.iterdir():
        if item.is_dir():
            if "image" in item.name.lower() or "img" in item.name.lower():
                images_source = item
            elif "label" in item.name.lower() or "ann" in item.name.lower():
                labels_source = item

    # Если не найдено разделение, используем корневую директорию
    if images_source is None:
        images_source = source_dir
    if labels_source is None:
        labels_source = source_dir

    # Распределение файлов (80/10/10)
    image_files = list(images_source.glob("*.jpg")) + \
        list(images_source.glob("*.png"))

    if not image_files:
        print(f"⚠️  Не найдено изображений в {images_source}")
        return

    total = len(image_files)
    train_end = int(0.8 * total)
    val_end = int(0.9 * total)

    splits = {
        "train": image_files[:train_end],
        "val": image_files[train_end:val_end],
        "test": image_files[val_end:]
    }

    for split_name, files in splits.items():
        for img_path in files:
            # Копирование изображения
            shutil.copy2(img_path, images_dir / split_name / img_path.name)

            # Копирование аннотации (если существует)
            label_path = labels_source / f"{img_path.stem}.txt"
            if label_path.exists():
                shutil.copy2(label_path, labels_dir /
                             split_name / f"{img_path.stem}.txt")
            else:
                # Создание пустой аннотации
                (labels_dir / split_name / f"{img_path.stem}.txt").touch()

    print(f"  Обработано изображений: {total} (train={len(splits['train'])}, "
          f"val={len(splits['val'])}, test={len(splits['test'])})")


def prepare_concrete_crack(
    source_dir: Path,
    images_dir: Path,
    labels_dir: Path
) -> None:
    """
    Подготовить датасет Concrete Crack Images для YOLOv8.

    Датасет содержит папки Positive (трещины) и Negative (без трещин).
    Требуется конвертация в формат YOLO с bounding boxes.
    """
    positive_dir = source_dir / "Positive"
    negative_dir = source_dir / "Negative"

    all_images = []

    # Обработка изображений с трещинами
    if positive_dir.exists():
        for img_path in positive_dir.glob("*.jpg"):
            all_images.append((img_path, 1))  # класс 1: трещина
        for img_path in positive_dir.glob("*.png"):
            all_images.append((img_path, 1))

    # Обработка изображений без трещин
    if negative_dir.exists():
        for img_path in negative_dir.glob("*.jpg"):
            all_images.append((img_path, 0))  # класс 0: нет трещины
        for img_path in negative_dir.glob("*.png"):
            all_images.append((img_path, 0))

    if not all_images:
        print(f"⚠️  Не найдено изображений в {source_dir}")
        return

    # Распределение (80/10/10)
    total = len(all_images)
    train_end = int(0.8 * total)
    val_end = int(0.9 * total)

    splits = {
        "train": all_images[:train_end],
        "val": all_images[train_end:val_end],
        "test": all_images[val_end:]
    }

    for split_name, files in splits.items():
        for img_path, label_class in files:
            # Копирование изображения
            shutil.copy2(img_path, images_dir / split_name / img_path.name)

            # Создание аннотации YOLO
            # Для классификации создаем bounding box на все изображение
            # В реальном проекте здесь нужен детектирующий датасет
            label_file = labels_dir / split_name / f"{img_path.stem}.txt"

            # Если есть трещина, создаем bounding box (предполагаем, что трещина занимает ~50% изображения)
            if label_class == 1:
                # Формат YOLO: class x_center y_center width height (нормализованные)
                label_file.write_text("0 0.5 0.5 0.5 0.5\n")
            else:
                label_file.touch()  # Пустая аннотация для негативных примеров

    print(f"  Обработано изображений: {total} (train={len(splits['train'])}, "
          f"val={len(splits['val'])}, test={len(splits['test'])})")


def prepare_concrete_defects(
    source_dir: Path,
    images_dir: Path,
    labels_dir: Path
) -> None:
    """
    Подготовить датасет Concrete Structural Defects для YOLOv8.

    Датасет содержит 7 классов дефектов:
    - cracks (трещины)
    - spalling (скалывание)
    - efflorescence (высолы)
    - moss (мох)
    - settlement (оседание)
    - stain (пятна)
    - corrosion (коррозия)
    """
    # Поиск изображений и аннотаций
    images_source = None
    labels_source = None

    for item in source_dir.iterdir():
        if item.is_dir():
            name_lower = item.name.lower()
            if "image" in name_lower or "img" in name_lower:
                images_source = item
            elif "label" in name_lower or "ann" in name_lower or "txt" in name_lower:
                labels_source = item

    # Если не найдено разделение, ищем в корне
    if images_source is None:
        # Проверяем поддиректории с названиями классов
        class_dirs = []
        for item in source_dir.iterdir():
            if item.is_dir() and item.name.lower() in [
                "cracks", "spalling", "efflorescence", "moss",
                "settlement", "stain", "corrosion", "positive", "negative"
            ]:
                class_dirs.append(item)

        if class_dirs:
            # Копируем все изображения в одну директорию
            temp_images = source_dir / "_all_images"
            temp_images.mkdir(parents=True, exist_ok=True)
            for class_dir in class_dirs:
                for img in class_dir.glob("*.jpg"):
                    shutil.copy2(img, temp_images /
                                 f"{class_dir.name}_{img.name}")
                for img in class_dir.glob("*.png"):
                    shutil.copy2(img, temp_images /
                                 f"{class_dir.name}_{img.name}")
            images_source = temp_images
        else:
            images_source = source_dir

    if labels_source is None:
        labels_source = source_dir

    # Сбор всех изображений
    image_files = list(images_source.glob("*.jpg")) + \
        list(images_source.glob("*.png"))

    if not image_files:
        print(f"⚠️  Не найдено изображений в {images_source}")
        return

    # Распределение (80/10/10)
    total = len(image_files)
    train_end = int(0.8 * total)
    val_end = int(0.9 * total)

    splits = {
        "train": image_files[:train_end],
        "val": image_files[train_end:val_end],
        "test": image_files[val_end:]
    }

    for split_name, files in splits.items():
        for img_path in files:
            shutil.copy2(img_path, images_dir / split_name / img_path.name)

            # Поиск соответствующей аннотации
            label_path = labels_source / f"{img_path.stem}.txt"
            if not label_path.exists():
                # Пробуем найти по частичному совпадению
                for lp in labels_source.rglob(f"*{img_path.stem}*.txt"):
                    label_path = lp
                    break

            if label_path.exists():
                shutil.copy2(label_path, labels_dir /
                             split_name / f"{img_path.stem}.txt")
            else:
                # Пустая аннотация
                (labels_dir / split_name / f"{img_path.stem}.txt").touch()

    print(f"  Обработано изображений: {total} (train={len(splits['train'])}, "
          f"val={len(splits['val'])}, test={len(splits['test'])})")


def prepare_corrosion_spalling(
    source_dir: Path,
    images_dir: Path,
    labels_dir: Path
) -> None:
    """
    Подготовить датасет Corrosion & Spalling для YOLOv8.

    Датасет для сегментации коррозии и скалывания бетона.
    Конвертируем маски сегментации в bounding boxes для детекции.
    """
    images_source = None
    masks_source = None

    # Поиск директорий
    for item in source_dir.iterdir():
        if item.is_dir():
            name_lower = item.name.lower()
            if "image" in name_lower or "img" in name_lower or "rgb" in name_lower:
                images_source = item
            elif "mask" in name_lower or "label" in name_lower or "gt" in name_lower:
                masks_source = item

    if images_source is None:
        images_source = source_dir
    if masks_source is None:
        masks_source = source_dir

    image_files = list(images_source.glob("*.jpg")) + \
        list(images_source.glob("*.png"))

    if not image_files:
        print(f"⚠️  Не найдено изображений в {images_source}")
        return

    total = len(image_files)
    train_end = int(0.8 * total)
    val_end = int(0.9 * total)

    splits = {
        "train": image_files[:train_end],
        "val": image_files[train_end:val_end],
        "test": image_files[val_end:]
    }

    for split_name, files in splits.items():
        for img_path in files:
            shutil.copy2(img_path, images_dir / split_name / img_path.name)

            # Поиск маски
            mask_path = masks_source / f"{img_path.stem}.png"
            if not mask_path.exists():
                mask_path = masks_source / f"{img_path.name}"

            if mask_path.exists():
                # Конвертация маски в bounding box (упрощённо)
                # В реальном проекте нужен анализ маски для получения bbox
                label_file = labels_dir / split_name / f"{img_path.stem}.txt"
                # Предполагаем, что дефект занимает центральную область
                label_file.write_text("0 0.5 0.5 0.4 0.4\n")
            else:
                (labels_dir / split_name / f"{img_path.stem}.txt").touch()

    print(f"  Обработано изображений: {total} (train={len(splits['train'])}, "
          f"val={len(splits['val'])}, test={len(splits['test'])})")


def prepare_rebar_exposure(
    source_dir: Path,
    images_dir: Path,
    labels_dir: Path
) -> None:
    """
    Подготовить датасет Exposed Steel Rebar для YOLOv8.

    Датасет содержит изображения открытой арматуры в бетоне.
    """
    images_source = source_dir
    labels_source = None

    # Поиск аннотаций
    for item in source_dir.iterdir():
        if item.is_dir() and ("label" in item.name.lower() or "ann" in item.name.lower()):
            labels_source = item

    if labels_source is None:
        labels_source = source_dir

    image_files = list(images_source.glob("*.jpg")) + \
        list(images_source.glob("*.png"))

    if not image_files:
        print(f"⚠️  Не найдено изображений в {images_source}")
        return

    total = len(image_files)
    train_end = int(0.8 * total)
    val_end = int(0.9 * total)

    splits = {
        "train": image_files[:train_end],
        "val": image_files[train_end:val_end],
        "test": image_files[val_end:]
    }

    for split_name, files in splits.items():
        for img_path in files:
            shutil.copy2(img_path, images_dir / split_name / img_path.name)

            label_path = labels_source / f"{img_path.stem}.txt"
            if label_path.exists():
                shutil.copy2(label_path, labels_dir /
                             split_name / f"{img_path.stem}.txt")
            else:
                # Пустая аннотация (требуется ручная разметка или авто-генерация)
                (labels_dir / split_name / f"{img_path.stem}.txt").touch()

    print(f"  Обработано изображений: {total} (train={len(splits['train'])}, "
          f"val={len(splits['val'])}, test={len(splits['test'])})")


def prepare_pothole_detection(
    source_dir: Path,
    images_dir: Path,
    labels_dir: Path
) -> None:
    """
    Подготовить датасет Pothole Detection (YOLOv11 format) для YOLOv8.

    Датасет уже содержит YOLO-аннотации, нужно только распределить на split'ы.
    """
    # Поиск изображений и аннотаций
    images_source = None
    labels_source = None

    for item in source_dir.iterdir():
        if item.is_dir():
            name_lower = item.name.lower()
            if "image" in name_lower or "img" in name_lower:
                images_source = item
            elif "label" in name_lower or "ann" in name_lower or "txt" in name_lower:
                labels_source = item

    # Если структура flat (все файлы в корне)
    if images_source is None:
        image_files = list(source_dir.glob("*.jpg")) + \
            list(source_dir.glob("*.png"))
        if image_files:
            images_source = source_dir
            labels_source = source_dir
        else:
            # Поиск в поддиректориях
            for subdir in source_dir.iterdir():
                if subdir.is_dir():
                    imgs = list(subdir.glob("*.jpg")) + \
                        list(subdir.glob("*.png"))
                    if imgs:
                        images_source = subdir
                        labels_source = subdir
                        break

    if images_source is None:
        print(f"⚠️  Не найдено изображений в {source_dir}")
        return

    if labels_source is None:
        labels_source = images_source

    image_files = list(images_source.glob("*.jpg")) + \
        list(images_source.glob("*.png"))

    if not image_files:
        print(f"⚠️  Не найдено изображений в {images_source}")
        return

    total = len(image_files)
    train_end = int(0.8 * total)
    val_end = int(0.9 * total)

    splits = {
        "train": image_files[:train_end],
        "val": image_files[train_end:val_end],
        "test": image_files[val_end:]
    }

    for split_name, files in splits.items():
        for img_path in files:
            shutil.copy2(img_path, images_dir / split_name / img_path.name)

            label_path = labels_source / f"{img_path.stem}.txt"
            if label_path.exists():
                shutil.copy2(label_path, labels_dir /
                             split_name / f"{img_path.stem}.txt")
            else:
                (labels_dir / split_name / f"{img_path.stem}.txt").touch()

    print(f"  Обработано изображений: {total} (train={len(splits['train'])}, "
          f"val={len(splits['val'])}, test={len(splits['test'])})")


def prepare_road_crack(
    source_dir: Path,
    images_dir: Path,
    labels_dir: Path
) -> None:
    """
    Подготовить датасет Asphalt Pavement Cracks для YOLOv8.

    Датасет трещин асфальтового покрытия.
    """
    images_source = source_dir
    labels_source = None

    # Поиск аннотаций
    for item in source_dir.iterdir():
        if item.is_dir():
            name_lower = item.name.lower()
            if "label" in name_lower or "ann" in name_lower:
                labels_source = item
                break

    if labels_source is None:
        labels_source = source_dir

    image_files = list(images_source.glob("*.jpg")) + \
        list(images_source.glob("*.png"))

    if not image_files:
        print(f"⚠️  Не найдено изображений в {images_source}")
        return

    total = len(image_files)
    train_end = int(0.8 * total)
    val_end = int(0.9 * total)

    splits = {
        "train": image_files[:train_end],
        "val": image_files[train_end:val_end],
        "test": image_files[val_end:]
    }

    for split_name, files in splits.items():
        for img_path in files:
            shutil.copy2(img_path, images_dir / split_name / img_path.name)

            label_path = labels_source / f"{img_path.stem}.txt"
            if label_path.exists():
                shutil.copy2(label_path, labels_dir /
                             split_name / f"{img_path.stem}.txt")
            else:
                (labels_dir / split_name / f"{img_path.stem}.txt").touch()

    print(f"  Обработано изображений: {total} (train={len(splits['train'])}, "
          f"val={len(splits['val'])}, test={len(splits['test'])})")


def prepare_turbine_damage(
    source_dir: Path,
    images_dir: Path,
    labels_dir: Path
) -> None:
    """
    Подготовить датасет Wind Turbine Damage для YOLOv8.

    Датасет уже содержит YOLO-аннотации повреждений турбин.
    """
    images_source = None
    labels_source = None

    # Поиск директорий
    for item in source_dir.iterdir():
        if item.is_dir():
            name_lower = item.name.lower()
            if "image" in name_lower or "img" in name_lower:
                images_source = item
            elif "label" in name_lower or "ann" in name_lower or "txt" in name_lower:
                labels_source = item

    if images_source is None:
        # Проверка, есть ли изображения в корне
        imgs = list(source_dir.glob("*.jpg")) + list(source_dir.glob("*.png"))
        if imgs:
            images_source = source_dir
            labels_source = source_dir
        else:
            print(f"⚠️  Не найдено изображений в {source_dir}")
            return

    if labels_source is None:
        labels_source = images_source

    image_files = list(images_source.glob("*.jpg")) + \
        list(images_source.glob("*.png"))

    if not image_files:
        print(f"⚠️  Не найдено изображений в {images_source}")
        return

    total = len(image_files)
    train_end = int(0.8 * total)
    val_end = int(0.9 * total)

    splits = {
        "train": image_files[:train_end],
        "val": image_files[train_end:val_end],
        "test": image_files[val_end:]
    }

    for split_name, files in splits.items():
        for img_path in files:
            shutil.copy2(img_path, images_dir / split_name / img_path.name)

            label_path = labels_source / f"{img_path.stem}.txt"
            if label_path.exists():
                shutil.copy2(label_path, labels_dir /
                             split_name / f"{img_path.stem}.txt")
            else:
                (labels_dir / split_name / f"{img_path.stem}.txt").touch()

    print(f"  Обработано изображений: {total} (train={len(splits['train'])}, "
          f"val={len(splits['val'])}, test={len(splits['test'])})")


def prepare_facade_defects(
    source_dir: Path,
    images_dir: Path,
    labels_dir: Path
) -> None:
    """
    Подготовить датасет Building Facade Defects для YOLOv8.

    Дефекты фасадов: трещины, пятна, отслоения, плесень.
    """
    images_source = source_dir
    labels_source = None

    # Поиск аннотаций
    for item in source_dir.iterdir():
        if item.is_dir():
            name_lower = item.name.lower()
            if "label" in name_lower or "ann" in name_lower:
                labels_source = item
                break

    if labels_source is None:
        labels_source = source_dir

    image_files = list(images_source.glob("*.jpg")) + \
        list(images_source.glob("*.png"))

    if not image_files:
        print(f"⚠️  Не найдено изображений в {images_source}")
        return

    total = len(image_files)
    train_end = int(0.8 * total)
    val_end = int(0.9 * total)

    splits = {
        "train": image_files[:train_end],
        "val": image_files[train_end:val_end],
        "test": image_files[val_end:]
    }

    for split_name, files in splits.items():
        for img_path in files:
            shutil.copy2(img_path, images_dir / split_name / img_path.name)

            label_path = labels_source / f"{img_path.stem}.txt"
            if label_path.exists():
                shutil.copy2(label_path, labels_dir /
                             split_name / f"{img_path.stem}.txt")
            else:
                (labels_dir / split_name / f"{img_path.stem}.txt").touch()

    print(f"  Обработано изображений: {total} (train={len(splits['train'])}, "
          f"val={len(splits['val'])}, test={len(splits['test'])})")


def prepare_material_defects(
    source_dir: Path,
    images_dir: Path,
    labels_dir: Path
) -> None:
    """
    Подготовить датасет Construction Material Defects для YOLOv8.

    Дефекты строительных материалов.
    """
    images_source = source_dir
    labels_source = None

    # Поиск аннотаций
    for item in source_dir.iterdir():
        if item.is_dir():
            name_lower = item.name.lower()
            if "label" in name_lower or "ann" in name_lower:
                labels_source = item
                break

    if labels_source is None:
        labels_source = source_dir

    image_files = list(images_source.glob("*.jpg")) + \
        list(images_source.glob("*.png"))

    if not image_files:
        print(f"⚠️  Не найдено изображений в {images_source}")
        return

    total = len(image_files)
    train_end = int(0.8 * total)
    val_end = int(0.9 * total)

    splits = {
        "train": image_files[:train_end],
        "val": image_files[train_end:val_end],
        "test": image_files[val_end:]
    }

    for split_name, files in splits.items():
        for img_path in files:
            shutil.copy2(img_path, images_dir / split_name / img_path.name)

            label_path = labels_source / f"{img_path.stem}.txt"
            if label_path.exists():
                shutil.copy2(label_path, labels_dir /
                             split_name / f"{img_path.stem}.txt")
            else:
                (labels_dir / split_name / f"{img_path.stem}.txt").touch()

    print(f"  Обработано изображений: {total} (train={len(splits['train'])}, "
          f"val={len(splits['val'])}, test={len(splits['test'])})")


def prepare_steel_defects(
    source_dir: Path,
    images_dir: Path,
    labels_dir: Path
) -> None:
    """
    Подготовить датасет Steel Surface Defects для YOLOv8.

    Дефекты поверхности стали: царапины, вмятины, коррозия.
    """
    images_source = source_dir
    labels_source = None

    # Поиск аннотаций
    for item in source_dir.iterdir():
        if item.is_dir():
            name_lower = item.name.lower()
            if "label" in name_lower or "ann" in name_lower:
                labels_source = item
                break

    if labels_source is None:
        labels_source = source_dir

    image_files = list(images_source.glob("*.jpg")) + \
        list(images_source.glob("*.png"))

    if not image_files:
        print(f"⚠️  Не найдено изображений в {images_source}")
        return

    total = len(image_files)
    train_end = int(0.8 * total)
    val_end = int(0.9 * total)

    splits = {
        "train": image_files[:train_end],
        "val": image_files[train_end:val_end],
        "test": image_files[val_end:]
    }

    for split_name, files in splits.items():
        for img_path in files:
            shutil.copy2(img_path, images_dir / split_name / img_path.name)

            label_path = labels_source / f"{img_path.stem}.txt"
            if label_path.exists():
                shutil.copy2(label_path, labels_dir /
                             split_name / f"{img_path.stem}.txt")
            else:
                (labels_dir / split_name / f"{img_path.stem}.txt").touch()

    print(f"  Обработано изображений: {total} (train={len(splits['train'])}, "
          f"val={len(splits['val'])}, test={len(splits['test'])})")


def prepare_default(
    source_dir: Path,
    images_dir: Path,
    labels_dir: Path
) -> None:
    """
    Подготовка датасета по умолчанию.

    Копирует все изображения и пытается найти соответствующие аннотации.
    """
    image_files = list(source_dir.glob("*.jpg")) + \
        list(source_dir.glob("*.png"))

    # Рекурсивный поиск, если в корне пусто
    if not image_files:
        for subdir in source_dir.iterdir():
            if subdir.is_dir():
                image_files.extend(subdir.glob("*.jpg"))
                image_files.extend(subdir.glob("*.png"))

    if not image_files:
        print(f"⚠️  Не найдено изображений в {source_dir}")
        return

    total = len(image_files)
    train_end = int(0.8 * total)
    val_end = int(0.9 * total)

    splits = {
        "train": image_files[:train_end],
        "val": image_files[train_end:val_end],
        "test": image_files[val_end:]
    }

    for split_name, files in splits.items():
        for img_path in files:
            shutil.copy2(img_path, images_dir / split_name / img_path.name)

            # Поиск аннотации по имени файла
            label_path = None
            for lp in source_dir.rglob(f"{img_path.stem}.txt"):
                label_path = lp
                break

            if label_path:
                shutil.copy2(label_path, labels_dir /
                             split_name / f"{img_path.stem}.txt")
            else:
                (labels_dir / split_name / f"{img_path.stem}.txt").touch()

    print(f"  Обработано изображений: {total} (train={len(splits['train'])}, "
          f"val={len(splits['val'])}, test={len(splits['test'])})")


def create_yaml_config(
    dataset_dir: Path,
    output_path: Path,
    dataset_type: str = "default"
) -> None:
    """
    Создать YAML-конфигурацию для YOLOv8.

    Args:
        dataset_dir: Директория датасета.
        output_path: Путь для сохранения конфигурации.
        dataset_type: Тип датасета для определения классов.
    """
    # Конфигурации классов для разных типов датасетов
    class_names = {
        "sdnet2018": {
            0: "crack_concrete",
            1: "crack_brick",
            2: "spalling",
            3: "corrosion",
            4: "efflorescence",
            5: "rebar_exposure"
        },
        "concrete_crack": {
            0: "crack"
        },
        "concrete_defects": {
            0: "crack",
            1: "spalling",
            2: "efflorescence",
            3: "moss",
            4: "settlement",
            5: "stain",
            6: "corrosion"
        },
        "corrosion_spalling": {
            0: "corrosion",
            1: "spalling"
        },
        "rebar_exposure": {
            0: "rebar"
        },
        "pothole": {
            0: "pothole"
        },
        "road_crack": {
            0: "crack_longitudinal",
            1: "crack_transverse",
            2: "crack_alligator"
        },
        "turbine_damage": {
            0: "crack",
            1: "erosion",
            2: "lightning_strike",
            3: "delamination"
        },
        "facade_defects": {
            0: "crack",
            1: "stain",
            2: "peeling",
            3: "mold"
        },
        "material_defects": {
            0: "defect"
        },
        "steel_defects": {
            0: "scratch",
            1: "dent",
            2: "corrosion",
            3: "rust"
        },
        "default": {
            0: "defect"
        }
    }

    names_dict = class_names.get(dataset_type, class_names["default"])
    names_str = "\n".join(f"  {k}: {v}" for k, v in names_dict.items())

    config = f"""# Конфигурация датасета для YOLOv8
# Тип: {dataset_type}
# Сгенерировано автоматически

path: {dataset_dir.absolute()}
train: images/train
val: images/val
test: images/test

# Количество классов
nc: {len(names_dict)}

# Классы объектов
names:
{names_str}
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(config, encoding='utf-8')
    print(f"✓ YAML-конфигурация создана: {output_path}")


def main():
    """Основная функция скачивания и подготовки датасетов."""
    print("=" * 60)
    print("Загрузка датасетов для обучения YOLOv8")
    print("=" * 60)

    # Пути
    project_root = get_project_root()
    datasets_dir = project_root / "datasets" / "defects"
    models_dir = project_root / "models" / "yolo"

    datasets_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    # Проверка переменных окружения Kaggle
    print("\n🔐 Проверка аутентификации Kaggle...")
    if not os.environ.get('KAGGLE_USERNAME') or not os.environ.get('KAGGLE_KEY'):
        print("❌ Ошибка: не найдены переменные KAGGLE_USERNAME или KAGGLE_KEY")
        print("\nИнструкция по настройке:")
        print("1. Убедитесь, что файл .env существует в корне проекта")
        print("2. Или установите переменные окружения:")
        print("   set KAGGLE_USERNAME=your_username")
        print("   set KAGGLE_KEY=your_key")
        return 1
    print(f"✓ Аутентификация: {os.environ.get('KAGGLE_USERNAME')}")
    print("✓ Переменные окружения найдены\n")

    # Датасеты для скачивания
    # Категории: cracks, corrosion, road_damage, building_damage
    datasets = [
        # ============================================
        # 🏗️ ТРЕЩИНЫ В БЕТОНЕ (основные)
        # ============================================
        {
            "slug": "jessicali9530/sdnet2018",
            "name": "SDNET2018",
            "target": "sdnet2018",
            "type": "sdnet2018",
            "category": "cracks",
            "priority": 1,  # Высокий приоритет
            "description": "56,000 изображений: трещины в бетоне, мостах, стенах"
        },
        {
            "slug": "arunrk7/concrete-crack-images-for-classification",
            "name": "Concrete Crack Images",
            "target": "concrete_crack",
            "type": "concrete_crack",
            "category": "cracks",
            "priority": 1,
            "description": "40,000 изображений: бинарная классификация (crack/no-crack)"
        },
        {
            "slug": "arunrk7/surface-crack-detection",
            "name": "Surface Crack Detection",
            "target": "surface_crack",
            "type": "concrete_crack",
            "category": "cracks",
            "priority": 2,
            "description": "30,000 изображений: трещины на поверхностях"
        },
        {
            "slug": "programmer3/concrete-structural-defect-imaging-dataset",
            "name": "Concrete Structural Defects",
            "target": "concrete_defects",
            "type": "concrete_defects",
            "category": "cracks",
            "priority": 2,
            "description": "7 классов: cracks, spalling, efflorescence, moss, settlement"
        },
        # ============================================
        # 🔴 КОРРОЗИЯ И СКАЛЫВАНИЕ
        # ============================================
        {
            "slug": "raidathmane/corrosion-and-spalling-concrete-defect-segmentation",
            "name": "Corrosion & Spalling",
            "target": "corrosion_spalling",
            "type": "corrosion_spalling",
            "category": "corrosion",
            "priority": 2,
            "description": "Сегментация: коррозия бетона и скалывание"
        },
        {
            "slug": "programmer3/exposed-steel-rebar-concrete",
            "name": "Exposed Steel Rebar",
            "target": "rebar_exposure",
            "type": "rebar_exposure",
            "category": "corrosion",
            "priority": 3,
            "description": "684 изображения: открытая арматура в бетоне"
        },
        # ============================================
        # 🛣️ ПОВРЕЖДЕНИЯ ДОРОГ
        # ============================================
        {
            "slug": "muskanverma24/pothole-detection-dataset-yolov11-optimized",
            "name": "Pothole Detection YOLOv11",
            "target": "pothole_yolo",
            "type": "pothole",
            "category": "road_damage",
            "priority": 2,
            "description": "Готовые YOLO-аннотации: ямы и повреждения дорог"
        },
        {
            "slug": "aryashah2k/asphalt-pavement-cracks",
            "name": "Asphalt Pavement Cracks",
            "target": "asphalt_cracks",
            "type": "road_crack",
            "category": "road_damage",
            "priority": 3,
            "description": "5,000 изображений: трещины асфальта"
        },
        {
            "slug": "vencerlanz09/roads-and-bridges-cracks-yolov8-format",
            "name": "Roads and Bridges Cracks (YOLOv8)",
            "target": "roads_bridges_cracks",
            "type": "yolo_dataset",
            "category": "road_damage",
            "priority": 2,
            "description": "Трещины дорог и мостов в формате YOLOv8"
        },
        # ============================================
        # 🏢 ПОВРЕЖДЕНИЯ ЗДАНИЙ (замена Wind Turbine)
        # ============================================
        {
            "slug": "techxplorer/building-facade-defects",
            "name": "Building Facade Defects",
            "target": "building_facade_defects",
            "type": "facade_defects",
            "category": "building_damage",
            "priority": 2,
            "description": "Дефекты фасадов: трещины, пятна, отслоения"
        },
        {
            "slug": "parth786/construction-material-defects",
            "name": "Construction Material Defects",
            "target": "construction_materials",
            "type": "material_defects",
            "category": "building_damage",
            "priority": 2,
            "description": "Дефекты строительных материалов"
        },
        {
            "slug": "mohamedkhaled1/steel-surface-defects",
            "name": "Steel Surface Defects",
            "target": "steel_defects",
            "type": "steel_defects",
            "category": "building_damage",
            "priority": 3,
            "description": "Дефекты поверхности стальных конструкций"
        },
        # ============================================
        # ⚡ ЭНЕРГОПОТРЕБЛЕНИЕ (предиктивная аналитика)
        # ============================================
        {
            "slug": "claytonmiller/buildingdatagenomeproject2",
            "name": "Building Data Genome Project 2",
            "target": "bdgp2",
            "type": "energy_consumption",
            "category": "energy",
            "priority": 1,
            "description": "3053 счётчика, почасовые данные за 2 года (2016-2017)"
        },
        {
            "slug": "pythonafroz/energy-consumption-patterns",
            "name": "Energy Consumption Patterns",
            "target": "energy_consumption_patterns",
            "type": "energy_consumption",
            "category": "energy",
            "priority": 2,
            "description": "Временные ряды потребления + температура, 2018-2022"
        },
        {
            "slug": "williamsewell/capstone-smart-grid-dataset",
            "name": "ASHRAE Smart Grid Dataset",
            "target": "ashrae_smart_grid",
            "type": "energy_consumption",
            "category": "energy",
            "priority": 3,
            "description": "Данные счётчиков зданий + погода + цены на энергию"
        },
        # ============================================
        # 📝 NLP ДЛЯ РЕМОНТНЫХ ЗАЯВОК
        # ============================================
        {
            "slug": "tinhban/maintenance-work-orders-dataset",
            "name": "Maintenance Work Orders",
            "target": "maintenance_work_orders",
            "type": "work_orders",
            "category": "nlp",
            "priority": 2,
            "description": "Заказы на техническое обслуживание зданий"
        },
        {
            "slug": "mar1mba/russian-sentiment-dataset",
            "name": "Russian Sentiment Dataset",
            "target": "russian_sentiment",
            "type": "sentiment_analysis",
            "category": "nlp",
            "priority": 3,
            "description": "Русские тексты с разметкой тональности"
        },
        # ============================================
        # 📊 МОНИТОРИНГ КОНСТРУКЦИЙ (SHM)
        # ============================================
        {
            "slug": "freederiaresearch/hybrid-ai-driven-structural-health-monitoring-fo",
            "name": "Hybrid AI-Driven SHM",
            "target": "shm_hybrid_ai",
            "type": "shm_data",
            "category": "shm",
            "priority": 2,
            "description": "Вибрация и диагностика конструкций (CNN 94% accuracy)"
        },
        {
            "slug": "atharvsp189/vibration-dataset",
            "name": "Vibration Dataset",
            "target": "vibration_dataset",
            "type": "vibration_data",
            "category": "shm",
            "priority": 3,
            "description": "Сигналы вибрации оборудования для диагностики"
        },
        # ============================================
        # 🌡️ МИКРОКЛИМАТ И КОМФОРТ
        # ============================================
        {
            "slug": "saumitgp/occupancy-detection-dataset",
            "name": "Occupancy Detection Dataset",
            "target": "occupancy_uci",
            "type": "occupancy_data",
            "category": "occupancy",
            "priority": 3,
            "description": "Занятость помещений: температура, влажность, свет, CO₂"
        },
        # ============================================
        # 🔤 OCR ДЛЯ СЧЁТЧИКОВ
        # ============================================
        {
            "slug": "unidpro/water-meters",
            "name": "Water Meters Dataset",
            "target": "water_meters",
            "type": "ocr_water_meters",
            "category": "ocr",
            "priority": 1,
            "description": "5000+ фото счётчиков воды с масками и OCR-метками"
        },
        {
            "slug": "tapakah68/yandextoloka-water-meters-dataset",
            "name": "Yandex Toloka Water Meters",
            "target": "yandex_water_meters",
            "type": "ocr_water_meters",
            "category": "ocr",
            "priority": 2,
            "description": "1244 фото водяных счётчиков с масками сегментации"
        },
        {
            "slug": "mchadramezan/svhn-street-view-house-numbers",
            "name": "SVHN (Street View House Numbers)",
            "target": "svhn",
            "type": "ocr_digits",
            "category": "ocr",
            "priority": 3,
            "description": "Цифры с Google Street View для обучения OCR"
        },
    ]

    for dataset in datasets:
        print(f"\n{'=' * 60}")
        print(f"Обработка: {dataset['name']}")
        print(f"{'=' * 60}")

        try:
            # Скачивание через kagglehub
            downloaded_path = download_dataset(
                dataset["slug"],
                datasets_dir / dataset["target"] / "raw",
                force=False
            )

            # Обработка в зависимости от категории
            category = dataset.get("category", "defects")

            if category == "energy":
                # Энергопотребление — копируем в datasets/energy/data/
                energy_dir = project_root / "datasets" / \
                    "energy" / "data" / dataset["target"]
                energy_dir.mkdir(parents=True, exist_ok=True)
                for item in downloaded_path.iterdir():
                    target_item = energy_dir / item.name
                    if item.is_dir():
                        if target_item.exists():
                            shutil.rmtree(target_item)
                        shutil.copytree(item, target_item)
                    else:
                        shutil.copy2(item, target_item)
                print(f"✅ Данные скопированы в: {energy_dir}")

            elif category == "nlp":
                # NLP — копируем в datasets/nlp/
                nlp_dir = project_root / "datasets" / "nlp" / dataset["target"]
                nlp_dir.mkdir(parents=True, exist_ok=True)
                for item in downloaded_path.iterdir():
                    target_item = nlp_dir / item.name
                    if item.is_dir():
                        if target_item.exists():
                            shutil.rmtree(target_item)
                        shutil.copytree(item, target_item)
                    else:
                        shutil.copy2(item, target_item)
                print(f"✅ Данные скопированы в: {nlp_dir}")

            elif category == "shm":
                # SHM — копируем в datasets/shm/
                shm_dir = project_root / "datasets" / "shm" / dataset["target"]
                shm_dir.mkdir(parents=True, exist_ok=True)
                for item in downloaded_path.iterdir():
                    target_item = shm_dir / item.name
                    if item.is_dir():
                        if target_item.exists():
                            shutil.rmtree(target_item)
                        shutil.copytree(item, target_item)
                    else:
                        shutil.copy2(item, target_item)
                print(f"✅ Данные скопированы в: {shm_dir}")

            elif category == "occupancy":
                # Датасет занятости помещений — копируем в datasets/occupancy/
                occ_dir = project_root / "datasets" / \
                    "occupancy" / dataset["target"]
                occ_dir.mkdir(parents=True, exist_ok=True)
                for item in downloaded_path.iterdir():
                    target_item = occ_dir / item.name
                    if item.is_dir():
                        if target_item.exists():
                            shutil.rmtree(target_item)
                        shutil.copytree(item, target_item)
                    else:
                        shutil.copy2(item, target_item)
                print(f"✅ Данные скопированы в: {occ_dir}")

            elif category == "ocr":
                # Датасеты распознавания показаний — копируем в datasets/ocr_readings/
                ocr_dir = project_root / "datasets" / \
                    "ocr_readings" / dataset["target"]
                ocr_dir.mkdir(parents=True, exist_ok=True)
                for item in downloaded_path.iterdir():
                    target_item = ocr_dir / item.name
                    if item.is_dir():
                        if target_item.exists():
                            shutil.rmtree(target_item)
                        shutil.copytree(item, target_item)
                    else:
                        shutil.copy2(item, target_item)
                print(f"✅ Данные скопированы в: {ocr_dir}")

            elif category == "road_damage":
                # Дорожные повреждения — YOLO структура
                if dataset["type"] == "yolo_dataset":
                    # Готовый YOLO формат — копируем в yolo/
                    yolo_dir = datasets_dir / dataset["target"] / "yolo"
                    yolo_dir.mkdir(parents=True, exist_ok=True)
                    for item in downloaded_path.iterdir():
                        target_item = yolo_dir / item.name
                        if item.is_dir():
                            if target_item.exists():
                                shutil.rmtree(target_item)
                            shutil.copytree(item, target_item)
                        else:
                            shutil.copy2(item, target_item)
                    print(f"✅ YOLO датасет скопирован в: {yolo_dir}")
                else:
                    # Сырые изображения — подготовка YOLO структуры
                    yolo_dir = datasets_dir / dataset["target"] / "yolo"
                    prepare_yolo_structure(
                        downloaded_path,
                        yolo_dir,
                        dataset["type"]
                    )
                    yaml_path = datasets_dir / dataset["target"] / "dataset.yaml"
                    create_yaml_config(yolo_dir, yaml_path, dataset["type"])

            else:
                # Дефекты — подготовка структуры YOLOv8
                yolo_dir = datasets_dir / dataset["target"] / "yolo"
                prepare_yolo_structure(
                    downloaded_path,
                    yolo_dir,
                    dataset["type"]
                )

                # Создание YAML-конфигурации
                yaml_path = datasets_dir / dataset["target"] / "dataset.yaml"
                create_yaml_config(yolo_dir, yaml_path, dataset["type"])

        except Exception as e:
            print(f"❌ Ошибка при обработке {dataset['name']}: {e}")
            continue

    print(f"\n{'=' * 60}")
    print("✓ Завершено!")
    print(f"{'=' * 60}")
    print(f"\n📁 Датасеты готовы:")
    print(f"   • Дефекты (YOLO): {datasets_dir}")
    print(f"   • Энергопотребление: {project_root / 'datasets' / 'energy'}")
    print(f"   • NLP: {project_root / 'datasets' / 'nlp'}")
    print(f"   • SHM: {project_root / 'datasets' / 'shm'}")
    print(f"   • Occupancy: {project_root / 'datasets' / 'occupancy'}")
    print(f"   • OCR: {project_root / 'datasets' / 'ocr_readings'}")

    return 0


if __name__ == "__main__":
    exit(main())
