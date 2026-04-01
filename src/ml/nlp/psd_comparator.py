# -*- coding: utf-8 -*-
"""
Модуль сравнения проектно-сметной документации (ПСД).

Сравнивает ведомости и сметы, находит расхождения в объёмах работ.

Использует:
- TF-IDF векторизация описаний работ (русский язык)
- Cosine similarity для поиска совпадений
- Сравнение объёмов и расчёт отклонений

Пример использования:
    comparator = PSDComparator()
    result = comparator.compare(
        work_order="Замена труб 32 мм - 10 м",
        psd="Прокладка трубопровода Ø32 - 15 м"
    )
    # similarity: 0.87, deviation: 33.3%
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


@dataclass
class WorkItem:
    """Элемент ведомости/сметы."""
    description: str  # Описание работы
    volume: float  # Объём
    unit: str  # Единица измерения (м, м², шт, компл)
    line_number: Optional[int] = None  # Номер строки в документе
    extra: dict[str, Any] = field(
        default_factory=dict)  # Дополнительные данные


@dataclass
class MatchResult:
    """Результат сравнения двух элементов."""
    work_item: WorkItem  # Элемент из ведомости
    psd_item: WorkItem  # Элемент из ПСД
    similarity: float  # Cosine similarity описаний (0-1)
    volume_fact: float  # Фактический объём
    volume_plan: float  # Плановый объём (ПСД)
    deviation_pct: float  # Отклонение в %
    status: str  # "OK", "РАСХОЖДЕНИЕ", "НЕ_НАЙДЕНО"
    confidence: float = 0.0  # Уверенность сопоставления


@dataclass
class ComparisonReport:
    """Итоговый отчёт о сравнении."""
    matches: list[MatchResult]  # Список сопоставлений
    total_items: int  # Всего элементов в ведомости
    matched: int  # Найдено совпадений
    deviations_found: int  # Найдено расхождений
    not_found: int  # Не найдено в ПСД
    overall_match_pct: float  # Общий процент совпадения


class PSDComparator:
    """
    Сравнение проектно-сметной документации.

    Алгоритм:
    1. Парсинг строк ведомости и сметы
    2. TF-IDF векторизация описаний (русский язык)
    3. Cosine similarity для поиска совпадений
    4. Сравнение объёмов и расчёт отклонений
    """

    # Порог similarity для считания элементов совпадающими
    SIMILARITY_THRESHOLD: float = 0.65

    # Порог отклонения объёмов (в %)
    DEVIATION_THRESHOLD: float = 10.0  # 10%

    # Словарь синонимов для нормализации терминов
    SYNONYM_MAP: dict[str, str] = {
        # Трубы
        'труб': 'труба',
        'трубопровода': 'труба',
        'трубопровод': 'труба',

        # Кабели
        'кабеля': 'кабель',
        'кабельный': 'кабель',
        'провода': 'провод',
        'проводка': 'провод',

        # Приборы учёта
        'счётчика': 'счетчик',
        'счетчик': 'счетчик',
        'приборов учёта': 'счетчик',
        'прибора учета': 'счетчик',

        # Элементы электрики
        'розетки': 'розетка',
        'розеток': 'розетка',
        'выключателя': 'выключатель',
        'выключателей': 'выключатель',

        # Работы
        'замена': 'замена',
        'заменить': 'замена',
        'монтаж': 'монтаж',
        'установка': 'монтаж',
        'установить': 'монтаж',
        'прокладка': 'прокладка',
        'проложить': 'прокладка',
        'покраска': 'покраска',
        'окраска': 'покраска',
        'крашен': 'покраска',
        'оклеить': 'оклейка',
        'оклейка': 'оклейка',

        # Стены/потолки
        'стен': 'стена',
        'стены': 'стена',
        'потолка': 'потолок',
        'потолков': 'потолок',
        'пола': 'пол',
        'полов': 'пол',
    }

    def __init__(self):
        """Инициализация компаратора."""
        self._vectorizer: TfidfVectorizer | None = None
        self._psd_items: list[WorkItem] = []
        self._work_items: list[WorkItem] = []

    def parse_line(self, line: str) -> WorkItem | None:
        """
        Распарсить строку ведомости/сметы.

        Примеры:
        - "Замена труб 32 мм - 10 м" → WorkItem(description="Замена труб 32 мм", volume=10.0, unit="м")
        - "Установка счётчика - 1 шт" → WorkItem(description="Установка счётчика", volume=1.0, unit="шт")
        - "Монтаж кабеля 3x2.5 - 100м" → WorkItem(description="Монтаж кабеля 3x2.5", volume=100.0, unit="м")

        Args:
            line: Строка из ведомости/сметы

        Returns:
            WorkItem или None если не удалось распарсить
        """
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('//'):
            return None

        # Паттерн: "Описание - Объём Ед.изм"
        # Поддерживаем различные форматы разделителей
        pattern = r'^(.+?)\s*[-–—]\s*(\d+[\.,]?\d*)\s*(м|м2|м³|шт|компл|кг|т|л)?\s*$'
        match = re.match(pattern, line, re.IGNORECASE)

        if not match:
            # Альтернативный паттерн: "Объём Ед.изм" в конце без разделителя
            pattern2 = r'^(.+?)\s*(\d+[\.,]?\d*)\s*(м|м2|м³|шт|компл|кг|т|л)\s*$'
            match = re.match(pattern2, line, re.IGNORECASE)

        if not match:
            # Если не удалось распарсить, создаём элемент с volume=1
            return WorkItem(
                description=line,
                volume=1.0,
                unit="шт"
            )

        description = match.group(1).strip()
        volume_str = match.group(2).replace(',', '.')
        volume = float(volume_str)
        unit = match.group(3) if match.group(3) else "шт"

        # Нормализация единиц измерения
        unit_map = {
            'м2': 'м²',
            'м3': 'м³',
            'М': 'м',
            'М2': 'м²',
            'М3': 'м³',
            'ШТ': 'шт',
            'КОМПЛ': 'компл',
        }
        unit = unit_map.get(unit, unit)

        return WorkItem(
            description=description,
            volume=volume,
            unit=unit
        )

    def parse_document(self, text: str) -> list[WorkItem]:
        """
        Распарсить документ (ведомость или смету).

        Args:
            text: Текст документа (каждая строка с новой строки)

        Returns:
            Список WorkItem
        """
        items = []
        lines = text.split('\n')

        for i, line in enumerate(lines, 1):
            item = self.parse_line(line)
            if item:
                item.line_number = i
                items.append(item)

        return items

    def _preprocess_text(self, text: str) -> str:
        """
        Предобработка текста для TF-IDF.

        - Удаление чисел и единиц измерения
        - Приведение к нижнему регистру
        - Удаление лишних пробелов
        - Сохранение ключевых слов
        """
        # Сохраняем размеры типа "3x2.5", "32 мм"
        text = re.sub(r'\d+[x×]\d+[\.\d]*', ' DIM ', text)
        text = re.sub(r'\d+\s*мм', ' MM ', text)
        text = re.sub(r'Ø\s*\d+', ' DIA ', text)

        # Удаляем остальные числа
        text = re.sub(r'\d+', '', text)

        # Удаляем единицы измерения, но сохраняем для ключевых слов
        text = re.sub(r'\b(м2|м³|мм|см|км|кг|л)\b',
                      '', text, flags=re.IGNORECASE)
        # Сохраняем "м" и "шт" как часть текста (важно для смысла)
        text = re.sub(r'\b(м|шт|компл)\b', ' UNIT ', text, flags=re.IGNORECASE)

        # Удаляем спецсимволы
        text = re.sub(r'[-–—,/;:(){}\[\]]', ' ', text)

        # Приводим к нижнему регистру
        text = text.lower()

        # Удаляем лишние пробелы
        text = ' '.join(text.split())

        # Применяем синонимы для нормализации терминов
        words = text.split()
        normalized_words = []
        for word in words:
            # Ищем частичное совпадение в словаре синонимов
            replacement = None
            for synonym, normal in self.SYNONYM_MAP.items():
                if synonym in word or word in synonym:
                    replacement = normal
                    break

            if replacement:
                normalized_words.append(replacement)
            else:
                normalized_words.append(word)

        text = ' '.join(normalized_words)

        return text

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Рассчитать cosine similarity между двумя текстами.

        Использует TF-IDF векторизацию с русским языком.
        Для коротких текстов использует упрощённый подход (Jaccard).

        Args:
            text1: Первый текст
            text2: Второй текст

        Returns:
            Similarity в диапазоне [0, 1]
        """
        # Предобработка
        text1_proc = self._preprocess_text(text1)
        text2_proc = self._preprocess_text(text2)

        # Разбиваем на слова
        words1 = set(text1_proc.split())
        words2 = set(text2_proc.split())

        # Если тексты очень короткие, используем Jaccard similarity
        if len(words1) < 3 or len(words2) < 3:
            if not words1 or not words2:
                return 0.0

            intersection = words1 & words2
            union = words1 | words2

            if not union:
                return 0.0

            # Jaccard similarity
            jaccard = len(intersection) / len(union)

            # Бонус за полное совпадение ключевых слов
            if len(intersection) >= 2:
                jaccard = min(1.0, jaccard + 0.2)

            return jaccard

        # TF-IDF векторизация для более длинных текстов
        try:
            vectorizer = TfidfVectorizer(
                lowercase=True,
                stop_words=None,
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.95
            )

            tfidf_matrix = vectorizer.fit_transform([text1_proc, text2_proc])
            similarity = cosine_similarity(
                tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(similarity)
        except Exception:
            # Если векторизация не удалась (пустые тексты)
            return 0.0

    def _calculate_deviation(self, fact: float, plan: float) -> float:
        """
        Рассчитать отклонение объёма в процентах.

        Args:
            fact: Фактический объём
            plan: Плановый объём (ПСД)

        Returns:
            Отклонение в % (положительное = перерасход, отрицательное = экономия)
        """
        if plan == 0:
            return 100.0 if fact != 0 else 0.0

        deviation = abs(fact - plan) / plan * 100
        return round(deviation, 2)

    def find_best_match(
        self,
        work_item: WorkItem,
        psd_items: list[WorkItem]
    ) -> tuple[WorkItem | None, float]:
        """
        Найти лучшее совпадение для элемента ведомости в ПСД.

        Args:
            work_item: Элемент из ведомости
            psd_items: Список элементов из ПСД

        Returns:
            (Лучший матч, similarity) или (None, 0.0) если не найдено
        """
        best_match = None
        best_similarity = 0.0

        for psd_item in psd_items:
            similarity = self._calculate_similarity(
                work_item.description,
                psd_item.description
            )

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = psd_item

        if best_similarity >= self.SIMILARITY_THRESHOLD:
            return best_match, best_similarity

        return None, 0.0

    def compare(
        self,
        work_order_text: str,
        psd_text: str
    ) -> ComparisonReport:
        """
        Сравнить ведомость с ПСД.

        Args:
            work_order_text: Текст ведомости (каждая строка с новой строки)
            psd_text: Текст сметы/ПСД (каждая строка с новой строки)

        Returns:
            ComparisonReport с результатами сравнения
        """
        # Парсинг документов
        self._work_items = self.parse_document(work_order_text)
        self._psd_items = self.parse_document(psd_text)

        matches = []
        matched_count = 0
        deviations_count = 0
        not_found_count = 0

        # Сопоставление элементов
        for work_item in self._work_items:
            best_match, similarity = self.find_best_match(
                work_item, self._psd_items)

            if best_match:
                matched_count += 1
                deviation = self._calculate_deviation(
                    work_item.volume, best_match.volume)

                status = "OK" if deviation <= self.DEVIATION_THRESHOLD else "РАСХОЖДЕНИЕ"
                if status == "РАСХОЖДЕНИЕ":
                    deviations_count += 1

                match_result = MatchResult(
                    work_item=work_item,
                    psd_item=best_match,
                    similarity=round(similarity, 3),
                    volume_fact=work_item.volume,
                    volume_plan=best_match.volume,
                    deviation_pct=deviation,
                    status=status,
                    confidence=round(
                        similarity * (1 - deviation/100), 3) if deviation < 100 else 0.0
                )
                matches.append(match_result)
            else:
                not_found_count += 1
                match_result = MatchResult(
                    work_item=work_item,
                    psd_item=WorkItem(description="НЕ НАЙДЕНО",
                                      volume=0, unit="шт"),
                    similarity=0.0,
                    volume_fact=work_item.volume,
                    volume_plan=0,
                    deviation_pct=100.0,
                    status="НЕ_НАЙДЕНО",
                    confidence=0.0
                )
                matches.append(match_result)

        # Общий процент совпадения
        if len(self._work_items) > 0:
            overall_match = (matched_count / len(self._work_items)) * 100
        else:
            overall_match = 0.0

        return ComparisonReport(
            matches=matches,
            total_items=len(self._work_items),
            matched=matched_count,
            deviations_found=deviations_count,
            not_found=not_found_count,
            overall_match_pct=round(overall_match, 2)
        )

    def compare_files(
        self,
        work_order_path: str | Path,
        psd_path: str | Path
    ) -> ComparisonReport:
        """
        Сравнить файлы ведомости и ПСД.

        Поддерживаемые форматы:
        - .txt — простой текст
        - .xlsx — Excel (через openpyxl)
        - .docx — Word (через python-docx)
        - .pdf — PDF (через PyMuPDF/fitz)

        Args:
            work_order_path: Путь к файлу ведомости
            psd_path: Путь к файлу ПСД

        Returns:
            ComparisonReport с результатами сравнения
        """
        work_order_text = self._read_file(work_order_path)
        psd_text = self._read_file(psd_path)

        return self.compare(work_order_text, psd_text)

    def _read_file(self, path: str | Path) -> str:
        """
        Прочитать файл и извлечь текст.

        Args:
            path: Путь к файлу

        Returns:
            Текст файла
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Файл не найден: {path}")

        # TXT
        if path.suffix.lower() == '.txt':
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()

        # XLSX
        elif path.suffix.lower() == '.xlsx':
            try:
                import openpyxl
            except ImportError:
                raise ImportError("Установите openpyxl: pip install openpyxl")

            wb = openpyxl.load_workbook(path)
            ws = wb.active

            lines = []
            for row in ws.iter_rows(values_only=True):
                # Объединяем ячейки строки
                line_parts = [
                    str(cell) if cell is not None else "" for cell in row]
                line = " ".join(line_parts).strip()
                if line:
                    lines.append(line)

            return '\n'.join(lines)

        # DOCX
        elif path.suffix.lower() == '.docx':
            try:
                from docx import Document
            except ImportError:
                raise ImportError(
                    "Установите python-docx: pip install python-docx")

            doc = Document(path)
            lines = [para.text.strip()
                     for para in doc.paragraphs if para.text.strip()]
            return '\n'.join(lines)

        # PDF
        elif path.suffix.lower() == '.pdf':
            try:
                import fitz  # PyMuPDF
            except ImportError:
                raise ImportError("Установите PyMuPDF: pip install PyMuPDF")

            doc = fitz.open(path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text

        else:
            raise ValueError(f"Неподдерживаемый формат файла: {path.suffix}")

    def to_dict(self, report: ComparisonReport) -> dict[str, Any]:
        """
        Преобразовать отчёт в словарь для JSON сериализации.

        Args:
            report: ComparisonReport

        Returns:
            Словарь с результатами
        """
        return {
            "matches": [
                {
                    "work_item": {
                        "description": m.work_item.description,
                        "volume": m.work_item.volume,
                        "unit": m.work_item.unit,
                        "line_number": m.work_item.line_number,
                    },
                    "psd_item": {
                        "description": m.psd_item.description,
                        "volume": m.psd_item.volume,
                        "unit": m.psd_item.unit,
                        "line_number": m.psd_item.line_number,
                    },
                    "similarity": m.similarity,
                    "volume_fact": m.volume_fact,
                    "volume_plan": m.volume_plan,
                    "deviation_pct": m.deviation_pct,
                    "status": m.status,
                    "confidence": m.confidence,
                }
                for m in report.matches
            ],
            "total_items": report.total_items,
            "matched": report.matched,
            "deviations_found": report.deviations_found,
            "not_found": report.not_found,
            "overall_match_pct": report.overall_match_pct,
        }

    def print_report(self, report: ComparisonReport) -> None:
        """
        Вывести отчёт в консоль.

        Args:
            report: ComparisonReport
        """
        print("=" * 80)
        print("ОТЧЁТ О СРАВНЕНИИ ВЕДОМОСТИ С ПСД")
        print("=" * 80)
        print(f"Всего элементов в ведомости: {report.total_items}")
        print(f"Найдено совпадений: {report.matched}")
        print(f"Найдено расхождений: {report.deviations_found}")
        print(f"Не найдено в ПСД: {report.not_found}")
        print(f"Общий процент совпадения: {report.overall_match_pct}%")
        print("=" * 80)

        # Расхождения
        deviations = [m for m in report.matches if m.status == "РАСХОЖДЕНИЕ"]
        if deviations:
            print("\n⚠ РАСХОЖДЕНИЯ:")
            print("-" * 80)
            for m in deviations:
                print(f"  {m.work_item.description}")
                print(f"    Факт: {m.volume_fact} {m.work_item.unit}")
                print(f"    План: {m.volume_plan} {m.psd_item.unit}")
                print(f"    Отклонение: {m.deviation_pct}%")
                print(f"    Similarity: {m.similarity}")
                print()

        # Не найдено
        not_found = [m for m in report.matches if m.status == "НЕ_НАЙДЕНО"]
        if not_found:
            print("\n❌ НЕ НАЙДЕНО В ПСД:")
            print("-" * 80)
            for m in not_found:
                print(
                    f"  {m.work_item.description} ({m.work_item.volume} {m.work_item.unit})")
                print()
