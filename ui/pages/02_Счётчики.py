from __future__ import annotations

import requests
import streamlit as st

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

st.set_page_config(page_title="Счётчики", page_icon="📟", layout="wide")
st.title("Счётчики")
st.caption("Учёт показаний и статистика")


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
        resp = requests.get(f"{API_BASE_URL}/meters/stats/consumption", timeout=5)
        if resp.status_code != 200:
            return {}
        return resp.json()
    except Exception:
        return {}


stats = fetch_stats()
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Всего счётчиков", len(fetch_list("/meters")))
with col2:
    st.metric("Просрочена поверка", len(fetch_list("/meters/stats/due-verification")))
with col3:
    st.metric("Всего показаний", len(fetch_list("/meters")))

st.divider()

st.subheader("Счётчики")
meters = fetch_list("/meters")
if meters:
    st.dataframe(meters, use_container_width=True)
else:
    st.info("Данные не найдены.")

st.subheader("Статистика потребления")
if stats:
    st.json(stats)
else:
    st.info("Статистика недоступна.")
