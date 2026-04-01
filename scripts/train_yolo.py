#!/usr/bin/env python3
"""
Скрипт для fine-tuning YOLOv8 на датасете трещин.

Использует GPU (CUDA) при наличии, иначе CPU.
Сохраняет модель и логи метрик.

Пример использования:
    python scripts/train_yolo.py --dataset sdnet2018 --epochs 100 --batch 16
    python scripts/train_yolo.py --dataset concrete_crack --config models/yolo/yolov8n.yaml
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import torch
from ultralytics import YOLO
from ultralytics.cfg import get_cfg
from ultralytics.utils import LOGGER


def get_project_root() -> Path:
    """Получить корневую директорию проекта."""
    return Path(__file__).parent.parent


def setup_logging(log_dir: Path, level: int = logging.INFO) -> logging.Logger:
    """
    Настроить логирование.

    Args:
        log_dir: Директория для сохранения логов.
        level: Уровень логирования.

    Returns:
        Настроенный логгер.
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    # Формат логов
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)

    # Файловый обработчик
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_handler = logging.FileHandler(
        log_dir / f'train_{timestamp}.log', encoding='utf-8')
    file_handler.setFormatter(log_format)

    # Настройка логгера
    logger = logging.getLogger('yolo_training')
    logger.setLevel(level)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def check_cuda() -> Dict[str, Any]:
    """
    Проверить доступность CUDA и GPU.

    Returns:
        Информация о доступных устройствах.
    """
    info = {
        'cuda_available': torch.cuda.is_available(),
        'cuda_version': torch.version.cuda if torch.cuda.is_available() else None,
        'device_count': torch.cuda.device_count() if torch.cuda.is_available() else 0,
        'device_name': None,
        'device_memory': None
    }

    if torch.cuda.is_available():
        info['device_name'] = torch.cuda.get_device_name(0)
        info['device_memory'] = f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB"

    return info


def load_model(model_name: str, pretrained: bool = True) -> YOLO:
    """
    Загрузить модель YOLOv8.

    Args:
        model_name: Имя модели (yolov8n, yolov8s, yolov8m, etc.).
        pretrained: Использовать предобученные веса.

    Returns:
        Модель YOLO.
    """
    if pretrained:
        logger.info(f"Загрузка предобученной модели: {model_name}")
        model = YOLO(f'{model_name}.pt')
    else:
        logger.info(f"Создание модели с нуля: {model_name}")
        model = YOLO(model_name)

    return model


def train_model(
    model: YOLO,
    dataset_yaml: Path,
    epochs: int = 100,
    batch_size: int = 16,
    image_size: int = 640,
    device: Optional[str] = None,
    save_dir: Optional[Path] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Обучить модель YOLOv8.

    Args:
        model: Модель YOLO.
        dataset_yaml: Путь к YAML-конфигурации датасета.
        epochs: Количество эпох обучения.
        batch_size: Размер батча.
        image_size: Размер изображения.
        device: Устройство для обучения (cuda/cpu).
        save_dir: Директория для сохранения результатов.
        **kwargs: Дополнительные параметры для model.train().

    Returns:
        Результаты обучения.
    """
    train_args = {
        'data': str(dataset_yaml),
        'epochs': epochs,
        'batch': batch_size,
        'imgsz': image_size,
        'device': device or ('cuda' if torch.cuda.is_available() else 'cpu'),
        'workers': 4,
        'verbose': True,
        'project': str(save_dir) if save_dir else None,
        'name': 'yolo_crack_detection',
        'exist_ok': True,
        'patience': 50,
        'save': True,
        'plots': True,
        **kwargs
    }

    logger.info("Начало обучения модели...")
    logger.info(f"Параметры: {json.dumps(train_args, indent=2, default=str)}")

    results = model.train(**train_args)

    return results


def evaluate_model(
    model: YOLO,
    dataset_yaml: Path,
    save_dir: Path
) -> Dict[str, float]:
    """
    Оценить модель на тестовом датасете.

    Args:
        model: Обученная модель.
        dataset_yaml: Путь к YAML-конфигурации.
        save_dir: Директория для сохранения результатов.

    Returns:
        Метрики модели.
    """
    logger.info("Оценка модели на тестовом датасете...")

    results = model.val(
        data=str(dataset_yaml),
        save_dir=str(save_dir),
        plots=True,
        verbose=True
    )

    metrics = {
        'mAP50': float(results.box.map50),
        'mAP50-95': float(results.box.map),
        'precision': float(results.box.mp),
        'recall': float(results.box.mr),
        'fitness': float(results.fitness)
    }

    logger.info(f"Метрики модели:")
    for name, value in metrics.items():
        logger.info(f"  {name}: {value:.4f}")

    return metrics


def run_inference(
    model: YOLO,
    test_images_dir: Path,
    save_dir: Path,
    num_images: int = 5
) -> None:
    """
    Запустить inference на тестовых изображениях.

    Args:
        model: Модель YOLO.
        test_images_dir: Директория с тестовыми изображениями.
        save_dir: Директория для сохранения результатов.
        num_images: Количество изображений для обработки.
    """
    logger.info(f"Запуск inference на {num_images} тестовых изображениях...")

    test_images = list(test_images_dir.glob("*.jpg")) + \
        list(test_images_dir.glob("*.png"))
    test_images = test_images[:num_images]

    if not test_images:
        logger.warning("Не найдено тестовых изображений")
        return

    save_dir.mkdir(parents=True, exist_ok=True)

    for img_path in test_images:
        logger.info(f"Обработка: {img_path.name}")

        results = model.predict(
            source=str(img_path),
            save=True,
            save_dir=str(save_dir),
            conf=0.25,
            iou=0.45
        )

        # Логирование результатов
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                logger.info(f"  Найдено объектов: {len(boxes)}")
                for box in boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    logger.info(f"    Класс {cls}: confidence={conf:.3f}")


def save_metrics(metrics: Dict[str, float], save_path: Path) -> None:
    """
    Сохранить метрики в JSON файл.

    Args:
        metrics: Словарь с метриками.
        save_path: Путь для сохранения.
    """
    save_path.parent.mkdir(parents=True, exist_ok=True)

    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    logger.info(f"Метрики сохранены: {save_path}")


def main():
    """Основная функция обучения."""
    parser = argparse.ArgumentParser(
        description='Fine-tuning YOLOv8 для детектирования трещин',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python scripts/train_yolo.py --dataset sdnet2018 --epochs 100
  python scripts/train_yolo.py --dataset concrete_crack --batch 32 --img-size 512
  python scripts/train_yolo.py --model yolov8s.pt --epochs 50
        """
    )

    parser.add_argument(
        '--dataset',
        type=str,
        default='roads_bridges_cracks',
        choices=['sdnet2018', 'concrete_crack', 'roads_bridges_cracks'],
        help='Датасет для обучения (по умолчанию: roads_bridges_cracks)'
    )

    parser.add_argument(
        '--model',
        type=str,
        default='yolov8n.pt',
        help='Модель YOLOv8 (по умолчанию: yolov8n.pt)'
    )

    parser.add_argument(
        '--epochs',
        type=int,
        default=100,
        help='Количество эпох обучения (по умолчанию: 100)'
    )

    parser.add_argument(
        '--batch',
        type=int,
        default=16,
        help='Размер батча (по умолчанию: 16)'
    )

    parser.add_argument(
        '--img-size',
        type=int,
        default=640,
        help='Размер изображения (по умолчанию: 640)'
    )

    parser.add_argument(
        '--device',
        type=str,
        default=None,
        help='Устройство для обучения (cuda/cpu/0, по умолчанию: auto)'
    )

    parser.add_argument(
        '--no-pretrained',
        action='store_true',
        help='Не использовать предобученные веса'
    )

    parser.add_argument(
        '--inference-only',
        action='store_true',
        help='Только inference без обучения'
    )

    parser.add_argument(
        '--num-test-images',
        type=int,
        default=5,
        help='Количество изображений для inference (по умолчанию: 5)'
    )

    args = parser.parse_args()

    # Инициализация
    global logger

    project_root = get_project_root()

    # Директории
    datasets_dir = project_root / 'datasets' / 'defects' / args.dataset
    models_dir = project_root / 'models' / 'yolo'
    logs_dir = project_root / 'logs' / 'yolo'

    datasets_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Настройка логирования
    logger = setup_logging(logs_dir)

    # Информация о системе
    logger.info("=" * 60)
    logger.info("Обучение YOLOv8 для детектирования трещин")
    logger.info("=" * 60)

    cuda_info = check_cuda()
    logger.info(f"CUDA доступен: {cuda_info['cuda_available']}")
    if cuda_info['cuda_available']:
        logger.info(
            f"GPU: {cuda_info['device_name']} ({cuda_info['device_memory']})")
        logger.info(f"Версия CUDA: {cuda_info['cuda_version']}")

    # Проверка датасета
    # Для roads_bridges_cracks файл находится в yolo/ поддиректории
    if args.dataset == 'roads_bridges_cracks':
        yaml_path = datasets_dir / 'yolo' / 'data.yaml'
    else:
        yaml_path = datasets_dir / 'dataset.yaml'

    if not yaml_path.exists():
        logger.error(f"❌ YAML-конфигурация датасета не найдена: {yaml_path}")
        logger.error("Сначала запустите: python scripts/download_datasets.py")
        return 1

    logger.info(f"Датасет: {args.dataset}")
    logger.info(f"Конфигурация: {yaml_path}")

    # Загрузка модели
    model_name = args.model.replace(
        '.pt', '') if args.model.endswith('.pt') else args.model
    model = load_model(model_name, pretrained=not args.no_pretrained)

    if args.inference_only:
        # Только запуск инференса
        logger.info("Режим: только inference")

        # Для roads_bridges_cracks изображения в yolo/ поддиректории
        if args.dataset == 'roads_bridges_cracks':
            test_images_dir = datasets_dir / 'yolo' / 'images' / 'test'
        else:
            test_images_dir = datasets_dir / 'yolo' / 'images' / 'test'
        inference_dir = models_dir / f'{model_name}_inference'

        # Загрузка лучшей модели
        best_model_path = models_dir / model_name / 'weights' / 'best.pt'
        if best_model_path.exists():
            model = YOLO(str(best_model_path))
            logger.info(f"Загружена модель: {best_model_path}")

        run_inference(model, test_images_dir,
                      inference_dir, args.num_test_images)

    else:
        # Обучение
        logger.info("Режим: обучение + оценка + inference")

        # Обучение
        results = train_model(
            model=model,
            dataset_yaml=yaml_path,
            epochs=args.epochs,
            batch_size=args.batch,
            image_size=args.img_size,
            device=args.device,
            save_dir=models_dir / model_name
        )

        # Сохранение метрик обучения
        train_metrics = {
            'epochs': args.epochs,
            'batch_size': args.batch,
            'image_size': args.img_size,
            'model': model_name,
            'dataset': args.dataset,
            'final_fitness': float(results.fitness),
            'box_loss': float(results.box_loss),
            'cls_loss': float(results.cls_loss),
            'dfl_loss': float(results.dfl_loss)
        }
        save_metrics(train_metrics, models_dir /
                     model_name / 'train_metrics.json')

        # Оценка
        eval_metrics = evaluate_model(
            model=YOLO(str(models_dir / model_name / 'weights' / 'best.pt')),
            dataset_yaml=yaml_path,
            save_dir=models_dir / model_name / 'eval'
        )
        save_metrics(eval_metrics, models_dir /
                     model_name / 'eval_metrics.json')

        # Инференс на тестовых изображениях
        test_images_dir = datasets_dir / 'yolo' / 'images' / 'test'
        inference_dir = models_dir / model_name / 'inference'

        run_inference(
            model=YOLO(str(models_dir / model_name / 'weights' / 'best.pt')),
            test_images_dir=test_images_dir,
            save_dir=inference_dir,
            num_images=args.num_test_images
        )

    logger.info("=" * 60)
    logger.info("✓ Обучение завершено!")
    logger.info(f"Модель сохранена: {models_dir / model_name / 'weights'}")
    logger.info(f"Логи: {logs_dir}")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    exit(main())
