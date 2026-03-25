from __future__ import annotations

import requests
import streamlit as st

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

st.set_page_config(page_title="Ремонтные работы", page_icon="🛠️", layout="wide")
st.title("Ремонтные работы")
st.caption("Журнал заявок и статистика")


@st.cache_data(ttl=10)
def fetch_list(path: str) -> list:
    try:
        resp = requests.get(f"{API_BASE_URL}{path}", timeout=5)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


@st.cache_data(ttl=10)
def fetch_stats() -> dict:
    try:
        resp = requests.get(f"{API_BASE_URL}/repair/stats/summary", timeout=5)
        if resp.status_code != 200:
            return {}
        return resp.json()
    except Exception:
        return {}


stats = fetch_stats()
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Всего заявок", stats.get("total", 0))
with col2:
    st.metric("В работе", stats.get("in_progress", 0))
with col3:
    st.metric("Завершено", stats.get("completed", 0))
with col4:
    st.metric("Отменено", stats.get("cancelled", 0))

st.divider()

st.subheader("Список заявок")
requests_list = fetch_list("/repair/requests")
if requests_list:
    st.dataframe(requests_list, use_container_width=True)
else:
    st.info("Данные не найдены.")
