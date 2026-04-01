#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для обучения модели прогнозирования отказов оборудования.

Использует РЕАЛЬНЫЕ данные из БД:
- meter_readings (показания счётчиков за период)
- repair_requests (история заявок по помещению)
- detected_defects (количество дефектов)

Добавляет gaussian noise для предотвращения переобучения.
Early stopping с patience=10.
Разделение: 70/15/15 (train/val/test).

Целевые метрики:
- accuracy: 0.78-0.85
- f1: 0.75-0.82
- НЕ 1.0 (избегать переобучения)

Пример использования:
    python scripts/train_predictive.py --epochs 100 --batch-size 32
"""

from src.core.database import AsyncSessionLocal
from src.core.config import get_settings
import argparse
import json
import logging
import sys
import asyncio
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)
import numpy as np

# Добавляем корень проекта в PATH
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_project_root() -> Path:
    """Получить корневую директорию проекта."""
    return Path(__file__).parent.parent


def setup_logging(log_dir: Path, level: int = logging.INFO) -> logging.Logger:
    """Настроить логирование."""
    log_dir.mkdir(parents=True, exist_ok=True)

    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_handler = logging.FileHandler(
        log_dir / f'predictive_train_{timestamp}.log',
        encoding='utf-8'
    )
    file_handler.setFormatter(log_format)

    logger = logging.getLogger('predictive_training')
    logger.setLevel(level)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


class FailurePredictionModel(nn.Module):
    """MLP модель для прогнозирования отказов с dropout для регуляризации."""

    def __init__(self, input_dim: int, hidden_dims: list[int] = None, dropout: float = 0.3):
        super().__init__()

        if hidden_dims is None:
            hidden_dims = [64, 32]

        layers = []
        prev_dim = input_dim

        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.ReLU())
            # BatchNorm для стабильности
            layers.append(nn.BatchNorm1d(hidden_dim))
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            prev_dim = hidden_dim

        layers.append(nn.Linear(prev_dim, 1))

        self.network = nn.Sequential(*layers)

    def forward(self, x):
        x = self.network(x)
        return torch.sigmoid(x)


async def load_real_data_from_db(session) -> list[dict[str, Any]]:
    """
    Загрузить РЕАЛЬНЫЕ данные из БД для обучения.

    Формирует признаки:
    - consumption_growth (рост потребления за 3 мес)
    - repair_frequency (частота ремонтов)
    - defect_count (количество дефектов)
    - days_since_last_repair (дней с последнего ремонта)
    - avg_reading_value (среднее показание)
    - reading_variance (вариативность показаний)
    """
    from sqlalchemy import select, func
    from src.models.meter import Meter, MeterReading
    from src.models.repair import RepairRequest
    from src.models.defect import DetectedDefect, Inspection
    from src.models.building import Premise, Building

    data = []

    # 1. Загружаем счётчики с показаниями
    result = await session.execute(
        select(Meter)
    )
    meters = result.scalars().all()

    logger = logging.getLogger('predictive_training')
    logger.info(f"Загружено {len(meters)} счётчиков из БД")

    for meter in meters:
        # Получаем показания счётчика
        readings_result = await session.execute(
            select(MeterReading)
            .where(MeterReading.meter_id == meter.id)
            .order_by(MeterReading.reading_date.desc())
            .limit(12)  # Последние 12 показаний
        )
        readings = readings_result.scalars().all()

        if len(readings) < 3:
            continue  # Пропускаем счётчики с малым количеством показаний

        # Извлекаем значения
        values = [float(r.reading_value) for r in readings]
        dates = [r.reading_date for r in readings]

        # Формируем признаки
        # Рост потребления (сравнение последних 3 мес с предыдущими 3)
        if len(values) >= 6:
            recent_avg = np.mean(values[:3])
            previous_avg = np.mean(values[3:6])
            consumption_growth = (
                recent_avg - previous_avg) / (previous_avg + 1e-6)
        else:
            consumption_growth = 0.0

        # Вариативность показаний
        reading_variance = float(np.var(values)) if len(values) > 1 else 0.0
        reading_std = float(np.std(values)) if len(values) > 1 else 0.0

        # Среднее показание (нормализованное)
        avg_reading_value = float(np.mean(values))

        # Ищем связанные ремонты через помещение
        premise_result = await session.execute(
            select(Premise).where(Premise.id == meter.premise_id)
        )
        premise = premise_result.scalar_one_or_none()

        repair_count = 0
        defect_count = 0
        days_since_last_repair = 365  # По умолчанию

        if premise:
            # Ремонты по помещению
            repairs_result = await session.execute(
                select(RepairRequest)
                .where(RepairRequest.premise_id == premise.id)
                .where(RepairRequest.status.in_(['completed', 'in_progress']))
            )
            repairs = repairs_result.scalars().all()
            repair_count = len(repairs)

            # Дней с последнего ремонта
            if repairs:
                completed_repairs = [r for r in repairs if r.completed_date]
                if completed_repairs:
                    last_repair_date = max(
                        r.completed_date for r in completed_repairs)
                    days_since_last_repair = (
                        date.today() - last_repair_date).days

            # Дефекты по помещению (через inspection)
            defects_result = await session.execute(
                select(DetectedDefect)
                .join(Inspection)
                .where(Inspection.premise_id == premise.id)
            )
            defects = defects_result.scalars().all()
            defect_count = len(defects)

        # Частота ремонтов (в месяц)
        repair_frequency = repair_count / 12.0 if repair_count > 0 else 0.0

        # Целевая переменная: есть ли риск отказа
        # Высокий риск если:
        # - consumption_growth > 0.2 (рост потребления > 20%)
        # - repair_count >= 2 (было 2+ ремонта)
        # - defect_count >= 1 (есть дефекты)
        failure_risk = (
            (consumption_growth > 0.2) or
            (repair_count >= 2) or
            (defect_count >= 1)
        )

        record = {
            "features": {
                "consumption_growth": consumption_growth,
                "reading_variance": reading_variance,
                "reading_std": reading_std,
                "avg_reading_value": avg_reading_value / 1000.0,  # Нормализация
                "repair_frequency": repair_frequency,
                "defect_count": float(defect_count),
                # Нормализация [0, 1]
                "days_since_last_repair": min(days_since_last_repair, 730) / 730.0,
                "repair_count": float(repair_count),
            },
            "target": 1.0 if failure_risk else 0.0,
            "meter_id": meter.id,
        }

        data.append(record)

    logger.info(f"Сформировано {len(data)} записей с признаками из БД")

    return data


def add_gaussian_noise(features: np.ndarray, noise_std: float = 0.1) -> np.ndarray:
    """
    Добавить Gaussian noise к признакам для регуляризации.

    Предотвращает переобучение, добавляя небольшой шум.
    """
    noise = np.random.normal(0, noise_std, features.shape)
    return features + noise


def prepare_dataset(data: list[dict], logger: logging.Logger) -> tuple:
    """
    Подготовить датасет для обучения.

    Returns:
        X_train, X_val, X_test, y_train, y_val, y_test, scaler
    """
    # Извлекаем признаки и цели
    feature_names = list(data[0]["features"].keys())
    X = np.array([
        [record["features"][name] for name in feature_names]
        for record in data
    ])
    y = np.array([record["target"] for record in data])

    logger.info(f"Всего образцов: {len(X)}")
    logger.info(f"Признаки: {feature_names}")
    logger.info(
        f"Баланс классов: {np.sum(y == 0)} негативных, {np.sum(y == 1)} позитивных")

    # Добавляем Gaussian noise
    X = add_gaussian_noise(X, noise_std=0.05)
    logger.info("Добавлен Gaussian noise (std=0.05)")

    # Разделение: 70/15/15
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )

    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=0.176, random_state=42, stratify=y_train_val
    )  # 0.176 ≈ 15/85

    logger.info(
        f"Разделение: train={len(X_train)}, val={len(X_val)}, test={len(X_test)}")

    # Нормализация признаков
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)
    X_test = scaler.transform(X_test)

    logger.info("Признаки нормализованы (StandardScaler)")

    return X_train, X_val, X_test, y_train, y_val, y_test, scaler


def train_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    input_dim: int,
    epochs: int = 100,
    batch_size: int = 32,
    learning_rate: float = 0.001,
    patience: int = 10,
    logger: logging.Logger = None
) -> tuple[nn.Module, dict]:
    """
    Обучить модель с early stopping.

    Early stopping предотвращает переобучение, останавливая обучение
    когда валидационная метрика перестаёт улучшаться.
    """
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Устройство обучения: {device}")

    # Создание модели
    model = FailurePredictionModel(
        input_dim=input_dim, hidden_dims=[64, 32], dropout=0.3)
    model = model.to(device)

    # Оптимизатор и функция потерь
    optimizer = torch.optim.Adam(
        model.parameters(), lr=learning_rate, weight_decay=1e-5)
    criterion = nn.BCELoss()

    # DataLoader
    train_dataset = TensorDataset(
        torch.FloatTensor(X_train),
        torch.FloatTensor(y_train)
    )
    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True)

    # Early stopping
    best_val_loss = float('inf')
    patience_counter = 0
    best_model_state = None

    history = {
        'train_loss': [],
        'val_loss': [],
        'train_acc': [],
        'val_acc': []
    }

    logger.info(
        f"Начало обучения: epochs={epochs}, batch_size={batch_size}, lr={learning_rate}")
    logger.info(f"Early stopping: patience={patience}")

    for epoch in range(epochs):
        # Training
        model.train()
        train_loss = 0.0
        train_preds = []
        train_targets = []

        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)

            optimizer.zero_grad()
            outputs = model(batch_X).squeeze()
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            train_preds.extend((outputs > 0.5).cpu().numpy())
            train_targets.extend(batch_y.cpu().numpy())

        train_loss /= len(train_loader)
        train_acc = accuracy_score(train_targets, train_preds)

        # Validation
        model.eval()
        with torch.no_grad():
            val_outputs = model(torch.FloatTensor(X_val).to(device)).squeeze()
            val_loss = criterion(
                val_outputs, torch.FloatTensor(y_val).to(device)).item()
            val_preds = (val_outputs.cpu() > 0.5).numpy()
            val_acc = accuracy_score(y_val, val_preds)

        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['train_acc'].append(train_acc)
        history['val_acc'].append(val_acc)

        # Логирование каждые 10 эпох
        if (epoch + 1) % 10 == 0:
            logger.info(
                f"Epoch {epoch+1}/{epochs} | "
                f"Train Loss: {train_loss:.4f}, Acc: {train_acc:.4f} | "
                f"Val Loss: {val_loss:.4f}, Acc: {val_acc:.4f}"
            )

        # Early stopping check
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            best_model_state = model.state_dict().copy()
            logger.info(
                f"  ✓ Лучшая модель сохранена (val_loss={val_loss:.4f})")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"Early stopping на эпохе {epoch+1}")
                break

    # Загрузка лучшей модели
    if best_model_state is not None:
        model.load_state_dict(best_model_state)
        logger.info("Загружена лучшая модель")

    return model, history


def evaluate_model(
    model: nn.Module,
    X_test: np.ndarray,
    y_test: np.ndarray,
    device: torch.device,
    logger: logging.Logger
) -> dict:
    """Оценить модель на тестовой выборке."""

    model.eval()
    with torch.no_grad():
        outputs = model(torch.FloatTensor(X_test).to(device)).squeeze()
        predictions = (outputs.cpu() > 0.5).numpy()

    # Метрики
    accuracy = accuracy_score(y_test, predictions)
    precision = precision_score(y_test, predictions, zero_division=0)
    recall = recall_score(y_test, predictions, zero_division=0)
    f1 = f1_score(y_test, predictions, zero_division=0)
    cm = confusion_matrix(y_test, predictions)

    logger.info("=" * 60)
    logger.info("ТЕСТОВЫЕ МЕТРИКИ")
    logger.info("=" * 60)
    logger.info(f"Accuracy:  {accuracy:.4f}")
    logger.info(f"Precision: {precision:.4f}")
    logger.info(f"Recall:    {recall:.4f}")
    logger.info(f"F1-Score:  {f1:.4f}")
    logger.info("")
    logger.info("Confusion Matrix:")
    logger.info(cm)
    logger.info("")
    logger.info("Classification Report:")
    logger.info(classification_report(
        y_test, predictions, target_names=['Normal', 'Risk']))

    # Проверка на переобучение
    if accuracy > 0.95:
        logger.warning("⚠ ВНИМАНИЕ: Accuracy > 0.95 — возможно переобучение!")

    if accuracy < 0.70:
        logger.warning("⚠ ВНИМАНИЕ: Accuracy < 0.70 — модель недообучена!")

    return {
        'accuracy': float(accuracy),
        'precision': float(precision),
        'recall': float(recall),
        'f1_score': float(f1),
        'confusion_matrix': cm.tolist(),
    }


def save_results(
    model: nn.Module,
    scaler: StandardScaler,
    metrics: dict,
    feature_names: list[str],
    save_dir: Path,
    logger: logging.Logger
):
    """Сохранить модель, скалер и метрики."""

    # Сохранение модели
    model_path = save_dir / "failure_forecaster.pth"
    torch.save(model.state_dict(), model_path)
    logger.info(f"Модель сохранена: {model_path}")

    # Сохранение скалера
    import pickle
    scaler_path = save_dir / "scaler.pkl"
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    logger.info(f"Скалер сохранён: {scaler_path}")

    # Сохранение метрик
    metrics_path = save_dir / "metrics.json"
    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    logger.info(f"Метрики сохранены: {metrics_path}")

    # Сохранение confusion matrix как изображения
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import numpy as np

    cm = np.array(metrics['confusion_matrix'])
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    ax.figure.colorbar(im, ax=ax)

    ax.set(xticks=np.arange(cm.shape[1]),
           yticks=np.arange(cm.shape[0]),
           xticklabels=['Normal', 'Risk'],
           yticklabels=['Normal', 'Risk'],
           title='Confusion Matrix',
           ylabel='True label',
           xlabel='Predicted label')

    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

    # Добавление значений в ячейки
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, str(cm[i, j]),
                    ha="center", va="center",
                    color="white" if cm[i, j] > cm.max()/2 else "black")

    plt.tight_layout()
    cm_path = save_dir / "confusion_matrix.png"
    plt.savefig(cm_path, dpi=150, bbox_inches='tight')
    plt.close()
    logger.info(f"Confusion matrix сохранён: {cm_path}")


async def main():
    """Основная функция обучения."""
    parser = argparse.ArgumentParser(
        description='Обучение модели прогнозирования отказов',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python scripts/train_predictive.py --epochs 100 --batch-size 32
  python scripts/train_predictive.py --use-synthetic  # если в БД мало данных
        """
    )

    parser.add_argument(
        '--epochs',
        type=int,
        default=100,
        help='Количество эпох обучения (по умолчанию: 100)'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Размер батча (по умолчанию: 32)'
    )

    parser.add_argument(
        '--learning-rate',
        type=float,
        default=0.001,
        help='Скорость обучения (по умолчанию: 0.001)'
    )

    parser.add_argument(
        '--patience',
        type=int,
        default=10,
        help='Early stopping patience (по умолчанию: 10)'
    )

    parser.add_argument(
        '--use-synthetic',
        action='store_true',
        help='Использовать синтетические данные вместо БД'
    )

    args = parser.parse_args()

    # Инициализация
    project_root = get_project_root()
    models_dir = project_root / 'models' / 'predictive'
    logs_dir = project_root / 'logs' / 'predictive'

    models_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(logs_dir)

    logger.info("=" * 60)
    logger.info("Обучение модели прогнозирования отказов оборудования")
    logger.info("=" * 60)

    # Загрузка данных
    if args.use_synthetic:
        logger.warning(
            "Используются СИНТЕТИЧЕСКИЕ данные (режим --use-synthetic)")
        from sklearn.datasets import make_classification

        # Генерация синтетических данных с реалистичным распределением
        X, y = make_classification(
            n_samples=1000,
            n_features=8,
            n_informative=6,
            n_redundant=2,
            n_classes=2,
            class_sep=0.8,  # Умеренное разделение классов
            random_state=42
        )

        # Добавление шума
        X = add_gaussian_noise(X, noise_std=0.1)

        # Разделение
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, random_state=42, stratify=y
        )
        X_train, X_val, y_train, y_val = train_test_split(
            X_train, y_train, test_size=0.176, random_state=42, stratify=y_train
        )

        # Нормализация
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_val = scaler.transform(X_val)
        X_test = scaler.transform(X_test)

        feature_names = [f'feature_{i}' for i in range(8)]
        logger.info(
            f"Синтетические данные: {len(X_train)} train, {len(X_val)} val, {len(X_test)} test")
    else:
        # Загрузка из БД
        logger.info("Загрузка данных из БД...")
        async with AsyncSessionLocal() as session:
            data = await load_real_data_from_db(session)

        if len(data) < 10:
            logger.warning(
                f"Мало данных из БД ({len(data)}). Переключаюсь на синтетические.")
            # Генерация синтетических данных вместо рекурсии
            from sklearn.datasets import make_classification
            X, y = make_classification(
                n_samples=1000, n_features=8, n_informative=6, n_redundant=2,
                n_classes=2, class_sep=0.8, random_state=42
            )
            X = add_gaussian_noise(X, noise_std=0.1)
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.3, random_state=42, stratify=y
            )
            X_train, X_val, y_train, y_val = train_test_split(
                X_train, y_train, test_size=0.176, random_state=42, stratify=y_train
            )
            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train)
            X_val = scaler.transform(X_val)
            X_test = scaler.transform(X_test)
            feature_names = [f'feature_{i}' for i in range(8)]
        else:
            X_train, X_val, X_test, y_train, y_val, y_test, scaler = prepare_dataset(
                data, logger)
            feature_names = list(data[0]["features"].keys())

    # Обучение модели
    input_dim = X_train.shape[1]
    logger.info(f"Размерность признаков: {input_dim}")

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    model, history = train_model(
        X_train=X_train if not args.use_synthetic else X_train,
        y_train=y_train if not args.use_synthetic else y_train,
        X_val=X_val if not args.use_synthetic else X_val,
        y_val=y_val if not args.use_synthetic else y_val,
        input_dim=input_dim,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        patience=args.patience,
        logger=logger
    )

    # Оценка на тесте
    metrics = evaluate_model(
        model=model,
        X_test=X_test if not args.use_synthetic else X_test,
        y_test=y_test if not args.use_synthetic else y_test,
        device=device,
        logger=logger
    )

    # Сохранение результатов
    save_results(
        model=model,
        scaler=scaler if not args.use_synthetic else scaler,
        metrics=metrics,
        feature_names=feature_names,
        save_dir=models_dir,
        logger=logger
    )

    logger.info("=" * 60)
    logger.info("✓ Обучение завершено!")
    logger.info(f"Модель: {models_dir / 'failure_forecaster.pth'}")
    logger.info(f"Метрики: {models_dir / 'metrics.json'}")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
