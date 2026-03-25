from __future__ import annotations

import requests
import streamlit as st

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

st.set_page_config(page_title="Отчёты", page_icon="📄", layout="wide")
st.title("Отчёты")
st.caption("Генерация и просмотр отчётов")


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


st.subheader("Шаблоны отчётов")
templates = fetch_list("/reports/templates")
if templates:
    st.dataframe(templates, use_container_width=True)
else:
    st.info("Шаблоны не найдены.")

st.divider()

st.subheader("Список отчётов")
reports = fetch_list("/reports")
if reports:
    st.dataframe(reports, use_container_width=True)
else:
    st.info("Отчёты не найдены.")
