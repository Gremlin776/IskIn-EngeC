# -*- coding: utf-8 -*-
"""
Тест endpoint /api/v1/defects/detect
"""

import requests
import os

# Базовый URL API
BASE_URL = "http://127.0.0.1:8000"

# Путь к тестовому изображению
TEST_IMAGE = r"d:\VKR\IskIn EngeC\datasets\defects\roads_bridges_cracks\yolo\test\images\04168eeebk3f94229020b7d905d28c43-1-_JPG.rf.b7456ec9aed620a184c515508604468c.jpg"

# Токен авторизации (получить через login endpoint)
# Для теста используем заглушку - в реальном приложении нужен JWT
HEADERS = {
    "Authorization": "Bearer test_token"  # Заменить на реальный токен
}


def test_detect_endpoint():
    """Тестирование endpoint детекции дефектов"""

    if not os.path.exists(TEST_IMAGE):
        print(f"❌ Файл не найден: {TEST_IMAGE}")
        return

    print(f"📷 Тестовое изображение: {TEST_IMAGE}")
    print(f"📡 Отправка запроса на {BASE_URL}/api/v1/defects/detect...")

    try:
        with open(TEST_IMAGE, "rb") as f:
            files = {"file": (os.path.basename(TEST_IMAGE), f, "image/jpeg")}
            params = {"confidence_threshold": 0.25}

            response = requests.post(
                f"{BASE_URL}/api/v1/defects/detect",
                files=files,
                params=params,
                headers=HEADERS,
                timeout=30
            )

        print(f"\n📊 Статус код: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Успешно!")
            print(f"   Найдено дефектов: {result['total_defects']}")
            print(f"   Время обработки: {result['processing_time_ms']} мс")
            print(
                f"   Изображение с bbox: {len(result['image_with_boxes'])} символов (base64)")

            if result['defects']:
                print(f"\n🔍 Найденные дефекты:")
                for i, det in enumerate(result['defects'], 1):
                    print(
                        f"   {i}. {det['class_name_ru']} ({det['class_name']})")
                    print(f"      Уверенность: {det['confidence']:.2%}")
                    print(
                        f"      BBox: x={det['bbox']['x']:.1f}, y={det['bbox']['y']:.1f}, w={det['bbox']['width']:.1f}, h={det['bbox']['height']:.1f}")
                    print(f"      Severity: {det['severity']}")
        else:
            print(f"❌ Ошибка: {response.status_code}")
            print(f"   Ответ: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ Ошибка подключения. Убедитесь, что сервер запущен:")
        print("   python -m uvicorn src.api.main:app --reload")
    except requests.exceptions.Timeout:
        print("❌ Таймаут запроса")
    except Exception as e:
        print(f"❌ Ошибка: {type(e).__name__}: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("ТЕСТ ENDPOINT /api/v1/defects/detect")
    print("=" * 60)
    test_detect_endpoint()
