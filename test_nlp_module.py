# -*- coding: utf-8 -*-
"""
Тест модуля сравнения ПСД.
"""

from src.ml.nlp.psd_comparator import PSDComparator
from src.ml.nlp.repair_classifier import RepairClassifier

def test_psd_comparator():
    """Тест сравнения ПСД."""
    print("=" * 80)
    print("ТЕСТ СРАВНЕНИЯ ПСД")
    print("=" * 80)
    
    # Тестовые данные
    work_order = """
Замена труб 32 мм - 10 м
Установка счётчика воды - 1 шт
Монтаж кабеля 3x2.5 - 50 м
Установка розетки - 5 шт
Покраска стен - 20 м2
"""
    
    psd = """
Прокладка трубопровода Ø32 мм - 15 м
Монтаж приборов учёта - 2 шт
Прокладка кабеля 3x2.5 - 45 м
Монтаж розеток - 6 шт
Окраска поверхностей - 25 м2
"""
    
    # Сравнение
    comparator = PSDComparator()
    report = comparator.compare(work_order, psd)
    
    # Вывод результатов
    comparator.print_report(report)
    
    # JSON результат
    print("\n" + "=" * 80)
    print("JSON ОТЧЁТ:")
    print("=" * 80)
    import json
    result_dict = comparator.to_dict(report)
    print(json.dumps(result_dict, indent=2, ensure_ascii=False))
    
    return result_dict


def test_repair_classifier():
    """Тест классификатора ремонтов."""
    print("\n" + "=" * 80)
    print("ТЕСТ КЛАССИФИКАТОРА РЕМОНТОВ")
    print("=" * 80)
    
    # Тестовые заявки
    test_cases = [
        "Течёт кран на кухне",
        "Нет света в комнате",
        "Холодно, батарея не греет",
        "Обои отклеились",
        "Трещина в стене",
        "Лифт не едет",
        "Дым в коридоре",
        "Сломался дверной замок",
    ]
    
    classifier = RepairClassifier()
    
    for text in test_cases:
        result = classifier.predict(text)
        print(f"\nЗаявка: {text}")
        print(f"  → Тип: {result.type_name} ({result.type_code})")
        print(f"  → Уверенность: {result.confidence:.1%}")
    
    # Тест через API метод
    print("\n" + "=" * 80)
    print("API МЕТОД (suggest_type):")
    print("=" * 80)
    
    result = classifier.suggest_type("Сломался смеситель в ванной")
    print(f"Вход: {result['input_text']}")
    print(f"Результат: {result['suggested_type']['name']} ({result['suggested_type']['code']})")
    print(f"Уверенность: {result['confidence']:.1%}")
    
    return result


if __name__ == "__main__":
    # Тест сравнения ПСД
    psd_result = test_psd_comparator()
    
    # Тест классификатора
    classifier_result = test_repair_classifier()
    
    print("\n" + "=" * 80)
    print("✅ ТЕСТЫ ЗАВЕРШЕНЫ")
    print("=" * 80)
