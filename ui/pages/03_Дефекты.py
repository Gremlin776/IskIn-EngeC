# -*- coding: utf-8 -*-
"""
Страница детекции дефектов с помощью YOLOv8
"""

from __future__ import annotations

import requests
import streamlit as st
from PIL import Image
import base64
import io

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

# Авторизация
token = st.sidebar.text_input(
    "Токен доступа", type="password", key="defect_token")


def get_headers() -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


st.set_page_config(page_title="Дефекты", page_icon="🧱", layout="wide")
st.title("Дефекты")
st.caption("Детекция повреждений и статистика")


@st.cache_data(ttl=10)
def fetch_list(path: str) -> list:
    try:
        resp = requests.get(f"{API_BASE_URL}{path}",
                            timeout=5, headers=get_headers())
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


@st.cache_data(ttl=10)
def fetch_stats() -> dict:
    try:
        resp = requests.get(
            f"{API_BASE_URL}/defects/stats/summary", timeout=5, headers=get_headers())
        if resp.status_code != 200:
            return {}
        return resp.json()
    except Exception:
        return {}


# ============================================
# Загрузка и детекция дефектов
# ============================================

st.subheader("🔍 Детекция дефектов YOLOv8")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### Загрузка изображения")
    uploaded_file = st.file_uploader(
        "Загрузите фото конструкции",
        type=["jpg", "jpeg", "png"],
        help="Поддерживаются форматы JPEG и PNG"
    )

    confidence_threshold = st.slider(
        "Порог уверенности",
        min_value=0.1,
        max_value=0.9,
        value=0.25,
        step=0.05,
        help="Минимальная уверенность для отображения дефекта"
    )

    inspection_id = st.number_input(
        "ID обследования (опционально)",
        min_value=0,
        value=0,
        help="Если указано, результаты будут сохранены в БД"
    )

    detect_button = st.button("🚀 Запустить детекцию",
                              type="primary", disabled=not uploaded_file)

# Обработка детекции
detection_result = None
image_with_boxes = None

if detect_button and uploaded_file:
    with st.spinner("🔄 Анализ изображения..."):
        try:
            # Подготовка файла
            files = {"file": (uploaded_file.name, uploaded_file, "image/jpeg")}
            params = {
                "confidence_threshold": confidence_threshold,
            }
            if inspection_id > 0:
                params["inspection_id"] = inspection_id

            # Запрос к API
            response = requests.post(
                f"{API_BASE_URL}/defects/detect",
                files=files,
                params=params,
                headers=get_headers(),
                timeout=60
            )

            if response.status_code == 200:
                detection_result = response.json()
                # Декодируем изображение с bbox
                image_data = base64.b64decode(
                    detection_result["image_with_boxes"])
                image_with_boxes = Image.open(io.BytesIO(image_data))
            else:
                st.error(
                    f"❌ Ошибка API: {response.status_code}\n\n{response.text}")

        except requests.exceptions.ConnectionError:
            st.error("❌ Ошибка подключения. Убедитесь, что сервер запущен.")
        except Exception as e:
            st.error(f"❌ Ошибка: {type(e).__name__}: {e}")

# Отображение результатов
if detection_result:
    with col2:
        st.markdown("### Результат детекции")

        if image_with_boxes:
            st.image(image_with_boxes, caption="Изображение с bounding boxes",
                     use_container_width=True)

        # Метрики
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            st.metric("Найдено дефектов", detection_result["total_defects"])
        with col_meta2:
            st.metric("Время обработки",
                      f"{detection_result['processing_time_ms']:.0f} мс")

        # Таблица дефектов
        if detection_result["defects"]:
            st.markdown("### Найденные дефекты")

            # Формируем таблицу
            defects_data = []
            for i, det in enumerate(detection_result["defects"], 1):
                defects_data.append({
                    "№": i,
                    "Класс": f"{det['class_name_ru']} ({det['class_name']})",
                    "Уверенность": f"{det['confidence']:.1%}",
                    "Критичность": det['severity'],
                    "X": f"{det['bbox']['x']:.0f}",
                    "Y": f"{det['bbox']['y']:.0f}",
                    "Ширина": f"{det['bbox']['width']:.0f}",
                    "Высота": f"{det['bbox']['height']:.0f}",
                })

            st.table(defects_data)

            # Цветовая индикация критичности
            st.caption("Критичность: 🔴 high/critical | 🟡 medium | 🟢 low")

st.divider()

# ============================================
# Статистика
# ============================================

stats = fetch_stats()
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Классы дефектов", len(fetch_list("/defects/classes")))
with col2:
    st.metric("Инспекции", len(fetch_list("/defects/inspections")))
with col3:
    st.metric("Всего дефектов", stats.get("total", 0))

st.divider()

# ============================================
# Инспекции
# ============================================

st.subheader("📋 Инспекции")
inspections = fetch_list("/defects/inspections")
if inspections:
    st.dataframe(inspections, use_container_width=True)
else:
    st.info("Данные не найдены.")

st.divider()

# ============================================
# Статистика дефектов
# ============================================

st.subheader("📊 Статистика дефектов")
if stats:
    st.json(stats)
else:
    st.info("Статистика недоступна.")
