# -*- coding: utf-8 -*-
"""
Страница сравнения проектно-сметной документации (ПСД).
"""

from __future__ import annotations

import requests
import streamlit as st

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

# Авторизация
token = st.sidebar.text_input("Токен доступа", type="password", key="psd_token")

def get_headers() -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


st.set_page_config(page_title="ПСД Сравнение", page_icon="📊", layout="wide")
st.title("Сравнение ПСД")
st.caption("Сравнение ведомости выполненных работ с проектно-сметной документацией")


# ============================================
# Загрузка файлов
# ============================================

st.subheader("📄 Загрузка документов")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Ведомость работ")
    work_order_file = st.file_uploader(
        "Загрузите ведомость",
        type=["txt", "xlsx", "docx", "pdf"],
        help="Файл с перечнем выполненных работ",
        key="work_order"
    )
    
    work_order_text = st.text_area(
        "Или введите текст вручную",
        height=150,
        placeholder="Замена труб 32 мм - 10 м\nУстановка счётчика - 1 шт",
        key="work_order_text"
    )

with col2:
    st.markdown("### Проектно-сметная документация")
    psd_file = st.file_uploader(
        "Загрузите ПСД",
        type=["txt", "xlsx", "docx", "pdf"],
        help="Файл с плановыми работами по смете",
        key="psd"
    )
    
    psd_text = st.text_area(
        "Или введите текст вручную",
        height=150,
        placeholder="Прокладка трубопровода Ø32 - 15 м\nМонтаж приборов учёта - 2 шт",
        key="psd_text"
    )


# ============================================
# Параметры сравнения
# ============================================

st.divider()
st.subheader("⚙️ Параметры сравнения")

col_param1, col_param2 = st.columns(2)

with col_param1:
    similarity_threshold = st.slider(
        "Порог similarity (совпадения описаний)",
        min_value=0.0,
        max_value=1.0,
        value=0.65,
        step=0.05,
        help="Минимальная схожесть описаний для считания элементов совпадающими"
    )

with col_param2:
    deviation_threshold = st.slider(
        "Порог отклонения объёмов (%)",
        min_value=0.0,
        max_value=100.0,
        value=10.0,
        step=5.0,
        help="Максимальное допустимое отклонение объёмов в %"
    )


# ============================================
# Сравнение
# ============================================

compare_button = st.button("🔍 Сравнить", type="primary", disabled=not (work_order_file or work_order_text) or not (psd_file or psd_text))

comparison_result = None

if compare_button:
    # Определяем источники данных
    use_files = work_order_file and psd_file
    use_text = work_order_text and psd_text
    
    if use_files:
        # Сравнение файлов
        with st.spinner("🔄 Анализ файлов..."):
            try:
                files = {
                    "work_order": (work_order_file.name, work_order_file.getvalue(), "application/octet-stream"),
                    "psd": (psd_file.name, psd_file.getvalue(), "application/octet-stream")
                }
                params = {
                    "similarity_threshold": similarity_threshold,
                    "deviation_threshold": deviation_threshold
                }
                
                response = requests.post(
                    f"{API_BASE_URL}/psd/compare",
                    files=files,
                    params=params,
                    headers=get_headers(),
                    timeout=60
                )
                
                if response.status_code == 200:
                    comparison_result = response.json()
                else:
                    st.error(f"❌ Ошибка API: {response.status_code}\n\n{response.text}")
            
            except requests.exceptions.ConnectionError:
                st.error("❌ Ошибка подключения. Убедитесь, что сервер запущен.")
            except Exception as e:
                st.error(f"❌ Ошибка: {type(e).__name__}: {e}")
    
    elif use_text:
        # Сравнение текстов
        with st.spinner("🔄 Анализ текстов..."):
            try:
                params = {
                    "work_order_text": work_order_text,
                    "psd_text": psd_text,
                    "similarity_threshold": similarity_threshold,
                    "deviation_threshold": deviation_threshold
                }
                
                response = requests.get(
                    f"{API_BASE_URL}/psd/compare-text",
                    params=params,
                    headers=get_headers(),
                    timeout=60
                )
                
                if response.status_code == 200:
                    comparison_result = response.json()
                else:
                    st.error(f"❌ Ошибка API: {response.status_code}\n\n{response.text}")
            
            except requests.exceptions.ConnectionError:
                st.error("❌ Ошибка подключения. Убедитесь, что сервер запущен.")
            except Exception as e:
                st.error(f"❌ Ошибка: {type(e).__name__}: {e}")
    
    else:
        st.warning("⚠️ Загрузите файлы или введите текст для обоих документов")


# ============================================
# Результаты
# ============================================

if comparison_result:
    st.divider()
    st.subheader("📊 Результаты сравнения")
    
    # Общие метрики
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Всего элементов", comparison_result["total_items"])
    
    with col2:
        st.metric("Найдено совпадений", comparison_result["matched"])
    
    with col3:
        st.metric("Расхождения", comparison_result["deviations_found"])
    
    with col4:
        st.metric("Не найдено в ПСД", comparison_result["not_found"])
    
    # Общий процент совпадения
    overall_pct = comparison_result.get("overall_match_pct", 0)
    st.progress(overall_pct / 100)
    st.caption(f"Общий процент совпадения: {overall_pct}%")
    
    # Таблица сопоставлений
    st.divider()
    st.subheader("📋 Детальное сравнение")
    
    if comparison_result["matches"]:
        # Фильтры
        filter_status = st.selectbox(
            "Фильтр по статусу",
            options=["Все", "РАСХОЖДЕНИЕ", "НЕ_НАЙДЕНО", "OK"],
            key="filter_status"
        )
        
        # Подготовка данных для таблицы
        table_data = []
        for match in comparison_result["matches"]:
            if filter_status == "Все" or match["status"] == filter_status:
                table_data.append({
                    "№": match["work_item"].get("line_number", "-"),
                    "Описание работы": match["work_item"]["description"],
                    "Факт": f"{match['volume_fact']} {match['work_item']['unit']}",
                    "План": f"{match['volume_plan']} {match['psd_item']['unit']}",
                    "Отклонение": f"{match['deviation_pct']}%" if match["status"] == "РАСХОЖДЕНИЕ" else "-",
                    "Similarity": f"{match['similarity']:.0%}",
                    "Статус": match["status"],
                })
        
        if table_data:
            st.dataframe(table_data, use_container_width=True)
        else:
            st.info("Нет данных для отображения")
    
    # Расхождения
    deviations = [m for m in comparison_result["matches"] if m["status"] == "РАСХОЖДЕНИЕ"]
    if deviations:
        st.divider()
        st.subheader("⚠️ Найденные расхождения")
        
        for i, m in enumerate(deviations, 1):
            with st.expander(f"#{i} {m['work_item']['description']}"):
                col_f, col_p = st.columns(2)
                
                with col_f:
                    st.markdown("**Факт**")
                    st.write(f"Объём: {m['volume_fact']} {m['work_item']['unit']}")
                    st.write(f"Описание: {m['work_item']['description']}")
                
                with col_p:
                    st.markdown("**План (ПСД)**")
                    st.write(f"Объём: {m['volume_plan']} {m['psd_item']['unit']}")
                    st.write(f"Описание: {m['psd_item']['description']}")
                
                st.metric("Отклонение", f"{m['deviation_pct']}%")
                st.caption(f"Similarity описаний: {m['similarity']:.0%}")
    
    # Не найдено в ПСД
    not_found = [m for m in comparison_result["matches"] if m["status"] == "НЕ_НАЙДЕНО"]
    if not_found:
        st.divider()
        st.subheader("❌ Не найдено в ПСД")
        
        for m in not_found:
            st.warning(f"{m['work_item']['description']} ({m['volume_fact']} {m['work_item']['unit']})")


# ============================================
# Справка
# ============================================

st.divider()
with st.expander("📖 Справка"):
    st.markdown("""
    ### Как использовать:
    
    1. **Загрузите файлы** ведомости и ПСД или введите текст вручную
    2. **Настройте параметры:**
       - Порог similarity: минимальная схожесть описаний (0.65 = 65%)
       - Порог отклонения: максимальное допустимое расхождение объёмов (%)
    3. **Нажмите "Сравнить"**
    
    ### Поддерживаемые форматы:
    - TXT (простой текст)
    - XLSX (Excel)
    - DOCX (Word)
    - PDF
    
    ### Формат ввода текста:
    Каждая строка должна содержать:
    ```
    Описание работы - Объём Ед.изм
    ```
    
    Пример:
    ```
    Замена труб 32 мм - 10 м
    Установка счётчика - 1 шт
    Монтаж кабеля 3x2.5 - 100 м
    ```
    
    ### Алгоритм сравнения:
    1. Парсинг строк документов
    2. TF-IDF векторизация описаний (русский язык)
    3. Cosine similarity для поиска совпадений
    4. Сравнение объёмов и расчёт отклонений
    """)
