# -*- coding: utf-8 -*-
from __future__ import annotations

import requests
import streamlit as st

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

# Авторизация
token = st.sidebar.text_input("Токен доступа", type="password")

def get_headers() -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


st.set_page_config(page_title="Предиктивная аналитика", page_icon="📈", layout="wide")
st.title("Предиктивная аналитика")
st.caption("Прогнозы отказов и риски")


@st.cache_data(ttl=10)
def fetch_list(path: str) -> list:
    try:
        resp = requests.get(f"{API_BASE_URL}{path}", timeout=5, headers=get_headers())
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


@st.cache_data(ttl=10)
def fetch_json(path: str) -> dict:
    try:
        resp = requests.get(f"{API_BASE_URL}{path}", timeout=5, headers=get_headers())
        if resp.status_code != 200:
            return {}
        data = resp.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Всего прогнозов", len(fetch_list("/predictive/failures")))
with col2:
    st.metric("Риск зданий", len(fetch_list("/predictive/risk/buildings")))
with col3:
    st.metric("Риск оборудования", len(fetch_list("/predictive/risk/equipment")))

st.divider()

st.subheader("Прогнозы отказов")
failures = fetch_list("/predictive/failures")
if failures:
    st.dataframe(failures, use_container_width=True)
else:
    st.info("Прогнозы не найдены.")

st.subheader("Информация о модели")
model_info = fetch_json("/predictive/model-info")
if model_info:
    st.json(model_info)
else:
    st.info("Информация о модели недоступна.")
