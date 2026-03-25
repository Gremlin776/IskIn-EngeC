from __future__ import annotations

import requests
import streamlit as st

API_BASE_URL = "http://127.0.0.1:8000/api/v1"


st.set_page_config(
    page_title="Инженерный ИскИн — Дашборд",
    page_icon="🏗️",
    layout="wide",
)

st.title("Инженерный ИскИн")
st.caption("Дашборд и сводная статистика")


@st.cache_data(ttl=10)
def fetch_list(path: str) -> list:
    url = f"{API_BASE_URL}{path}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


def stat_card(label: str, value: int) -> None:
    st.metric(label, value)


col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    stat_card("Здания", len(fetch_list("/buildings")))
with col2:
    stat_card("Ремонт", len(fetch_list("/repair/requests")))
with col3:
    stat_card("Счётчики", len(fetch_list("/meters")))
with col4:
    stat_card("Дефекты", len(fetch_list("/defects/inspections")))
with col5:
    stat_card("Отчёты", len(fetch_list("/reports")))
with col6:
    stat_card("Прогнозы", len(fetch_list("/predictive/failures")))

st.divider()

st.subheader("Состояние сервиса")
health_col1, health_col2 = st.columns(2)

with health_col1:
    try:
        health = requests.get(f"{API_BASE_URL}/health", timeout=5).json()
        st.success("API доступен")
        st.json(health)
    except Exception:
        st.error("API недоступен")

with health_col2:
    st.info(
        "Используйте меню слева для перехода к разделам: ремонт, счётчики, дефекты, отчёты и прогнозы."
    )
