# -*- coding: utf-8 -*-
"""
Классификатор типов ремонтов на основе текстового описания.

Использует TF-IDF + LogisticRegression для определения типа ремонта.

Пример использования:
    classifier = RepairClassifier()
    result = classifier.predict("Течёт кран на кухне")
    # type_code: "plumbing", type_name: "Сантехника", confidence: 0.85
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import numpy as np


@dataclass
class RepairType:
    """Тип ремонта."""
    code: str  # Код типа (plumbing, electrical, etc.)
    name: str  # Название на русском
    name_short: str  # Краткое название
    keywords: list[str]  # Ключевые слова для классификации


@dataclass
class ClassificationResult:
    """Результат классификации."""
    type_code: str  # Код типа
    type_name: str  # Название на русском
    confidence: float  # Уверенность (0-1)
    all_probabilities: dict[str, float]  # Все вероятности


class RepairClassifier:
    """
    Классификатор типов ремонтов.

    Алгоритм:
    1. TF-IDF векторизация текста заявки
    2. LogisticRegression для классификации
    3. Возврат типа с наибольшей вероятностью

    Поддерживаемые типы:
    - plumbing: Сантехника
    - electrical: Электрика
    - hvac: Отопление/Вентиляция
    - finishing: Отделочные работы
    - structural: Строительные работы
    - elevator: Лифтовое оборудование
    - fire_safety: Пожарная безопасность
    - other: Прочее
    """

    # Предопределённые типы ремонтов
    REPAIR_TYPES: list[RepairType] = [
        RepairType(
            code="plumbing",
            name="Сантехнические работы",
            name_short="Сантехника",
            keywords=[
                "кран", "смеситель", "труба", "вода", "течь", "затоп",
                "унитаз", "раковина", "ванна", "душ", "канализация",
                "водопровод", "слив", "сифон", "вентиль", "задвижка"
            ]
        ),
        RepairType(
            code="electrical",
            name="Электротехнические работы",
            name_short="Электрика",
            keywords=[
                "свет", "розетка", "выключатель", "провод", "кабель",
                "автомат", "щиток", "лампа", "люстра", "напряжение",
                "электричество", "короткое замыкание", "проводка"
            ]
        ),
        RepairType(
            code="hvac",
            name="Отопление и вентиляция",
            name_short="Отопление",
            keywords=[
                "отопление", "батарея", "радиатор", "тепло", "холодно",
                "вентиляция", "кондиционер", "воздух", "труба отопления",
                "стояк", "теплоснабжение", "котел", "бойлер"
            ]
        ),
        RepairType(
            code="finishing",
            name="Отделочные работы",
            name_short="Отделка",
            keywords=[
                "обои", "краска", "штукатурка", "шпаклевка", "плитка",
                "ламинат", "линолеум", "потолок", "пол", "стена",
                "покраска", "клеить", "швы", "трещина"
            ]
        ),
        RepairType(
            code="structural",
            name="Строительные работы",
            name_short="Строительство",
            keywords=[
                "фундамент", "стена", "перекрытие", "кровля", "крыша",
                "фасад", "цоколь", "арматура", "бетон", "кирпич",
                "несущая", "конструкция", "деформация", "осадка"
            ]
        ),
        RepairType(
            code="elevator",
            name="Лифтовое оборудование",
            name_short="Лифт",
            keywords=[
                "лифт", "кабина", "шахта", "подъемник", "двери лифта",
                "кнопка лифта", "застрял", "не едет", "вызов лифта"
            ]
        ),
        RepairType(
            code="fire_safety",
            name="Пожарная безопасность",
            name_short="Пожарка",
            keywords=[
                "пожар", "дым", "извещатель", "датчик", "сигнализация",
                "огнетушитель", "пожарный", "эвакуация", "выход",
                "задымление", "тревога"
            ]
        ),
        RepairType(
            code="other",
            name="Прочие работы",
            name_short="Прочее",
            keywords=[
                "другое", "неизвестно", "разное"
            ]
        ),
    ]

    def __init__(self, model_path: Optional[str] = None):
        """
        Инициализация классификатора.

        Args:
            model_path: Путь к сохранённой модели (опционально)
        """
        self._model: Optional[Pipeline] = None
        self._is_trained = False
        self._model_path = model_path

        # Загрузка сохранённой модели
        if model_path and Path(model_path).exists():
            self.load_model(model_path)

    def _create_pipeline(self) -> Pipeline:
        """
        Создать ML пайплайн.

        Returns:
            Pipeline с TF-IDF и LogisticRegression
        """
        from sklearn import __version__ as sklearn_version

        # Проверка версии scikit-learn
        major_version = int(sklearn_version.split('.')[0])

        # В scikit-learn >= 1.5 параметр multi_class удалён
        if major_version >= 1:
            clf = LogisticRegression(
                max_iter=1000,
                solver='lbfgs',
                class_weight='balanced',
                random_state=42
            )
        else:
            clf = LogisticRegression(
                max_iter=1000,
                multi_class='multinomial',
                solver='lbfgs',
                class_weight='balanced',
                random_state=42
            )

        return Pipeline([
            ('tfidf', TfidfVectorizer(
                lowercase=True,
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.95,
                max_features=1000
            )),
            ('clf', clf)
        ])

    def train(self, training_data: list[tuple[str, str]]) -> None:
        """
        Обучить классификатор.

        Args:
            training_data: Список кортежей (текст, label)
                Пример: [("Течёт кран", "plumbing"), ("Нет света", "electrical")]
        """
        if not training_data:
            # Обучаем на ключевых словах если нет данных
            training_data = self._generate_training_from_keywords()

        texts = [text for text, _ in training_data]
        labels = [label for _, label in training_data]

        self._model = self._create_pipeline()
        self._model.fit(texts, labels)
        self._is_trained = True

    def _generate_training_from_keywords(self) -> list[tuple[str, str]]:
        """
        Сгенерировать тренировочные данные из ключевых слов.

        Returns:
            Список (текст, label) для обучения
        """
        training_data = []

        for repair_type in self.REPAIR_TYPES:
            # Создаём примеры из ключевых слов
            for keyword in repair_type.keywords:
                # Простые фразы с ключевым словом
                templates = [
                    f"{keyword}",
                    f"Проблема: {keyword}",
                    f"Нужно отремонтировать {keyword}",
                    f"Не работает {keyword}",
                    f"Сломался {keyword}",
                    f"Требуется замена {keyword}",
                    f"Повреждён {keyword}",
                ]
                for template in templates:
                    training_data.append((template, repair_type.code))

        return training_data

    def predict(self, text: str) -> ClassificationResult:
        """
        Классифицировать текст заявки.

        Args:
            text: Текст описания проблемы

        Returns:
            ClassificationResult с результатом
        """
        if not self._is_trained and not self._model:
            # Автоматическое обучение на ключевых словах
            self.train([])

        if not self._model:
            raise RuntimeError("Модель не обучена")

        # Предсказание
        prediction = self._model.predict([text])[0]
        probabilities = self._model.predict_proba([text])[0]

        # Получаем все вероятности
        all_probs = {}
        for i, label in enumerate(self._model.classes_):
            all_probs[label] = float(probabilities[i])

        # Находим тип ремонта
        repair_type = self._get_repair_type_by_code(prediction)

        # Уверенность
        confidence = float(max(probabilities))

        return ClassificationResult(
            type_code=prediction,
            type_name=repair_type.name if repair_type else prediction,
            confidence=round(confidence, 3),
            all_probabilities=all_probs
        )

    def _get_repair_type_by_code(self, code: str) -> Optional[RepairType]:
        """
        Получить тип ремонта по коду.

        Args:
            code: Код типа

        Returns:
            RepairType или None
        """
        for rt in self.REPAIR_TYPES:
            if rt.code == code:
                return rt
        return None

    def save_model(self, path: str | Path) -> None:
        """
        Сохранить модель в файл.

        Args:
            path: Путь для сохранения
        """
        if not self._model:
            raise RuntimeError("Модель не обучена")

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'wb') as f:
            pickle.dump(self._model, f)

        self._model_path = str(path)

    def load_model(self, path: str | Path) -> None:
        """
        Загрузить модель из файла.

        Args:
            path: Путь к модели
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Модель не найдена: {path}")

        with open(path, 'rb') as f:
            self._model = pickle.load(f)

        self._is_trained = True
        self._model_path = str(path)

    def get_all_types(self) -> list[dict[str, Any]]:
        """
        Получить все типы ремонтов.

        Returns:
            Список словарей с информацией о типах
        """
        return [
            {
                "code": rt.code,
                "name": rt.name,
                "name_short": rt.name_short,
                "keywords": rt.keywords,
            }
            for rt in self.REPAIR_TYPES
        ]

    def suggest_type(self, text: str) -> dict[str, Any]:
        """
        Предложить тип ремонта для текста.

        Удобный метод для API.

        Args:
            text: Текст описания проблемы

        Returns:
            Словарь с результатом
        """
        result = self.predict(text)

        return {
            "suggested_type": {
                "code": result.type_code,
                "name": result.type_name,
            },
            "confidence": result.confidence,
            "all_probabilities": result.all_probabilities,
            "input_text": text,
        }
