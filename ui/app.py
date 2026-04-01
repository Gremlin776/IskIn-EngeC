# -*- coding: utf-8 -*-
from __future__ import annotations

import requests
import streamlit as st

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

# Авторизация
token = st.sidebar.text_input("Токен доступа", type="password")

def get_headers() -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


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
        resp = requests.get(url, timeout=5, headers=get_headers())
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

st.subheader("Добавить здание")
with st.form("create_building", clear_on_submit=True):
    name = st.text_input("Название", max_chars=100)
    address = st.text_input("Адрес", max_chars=255)
    building_type = st.text_input("Тип (необязательно)", max_chars=50)
    year_built = st.number_input("Год постройки", min_value=1800, max_value=2100, value=2000)
    floors = st.number_input("Этажей", min_value=1, max_value=200, value=1)
    total_area = st.number_input("Площадь, м²", min_value=0.0, value=0.0, step=0.1)
    submitted = st.form_submit_button("Добавить здание")

    if submitted:
        payload = {
            "name": name.strip(),
            "address": address.strip(),
            "building_type": building_type.strip() or None,
            "year_built": int(year_built) if year_built else None,
            "floors": int(floors) if floors else None,
            "total_area": float(total_area) if total_area else None,
        }
        try:
            resp = requests.post(
                f"{API_BASE_URL}/buildings",
                json=payload,
                timeout=5,
                headers=get_headers(),
            )
            if resp.status_code in (200, 201):
                st.success("Здание добавлено")
                st.rerun()
            else:
                st.error(f"Ошибка: {resp.status_code} — {resp.text}")
        except Exception as exc:
            st.error(f"Ошибка запроса: {exc}")

st.divider()

st.subheader("Состояние сервиса")
health_col1, health_col2 = st.columns(2)

with health_col1:
    try:
        health = requests.get(f"{API_BASE_URL}/health", timeout=5, headers=get_headers()).json()
        st.success("API доступен")
        st.json(health)
    except Exception:
        st.error("API недоступен")

with health_col2:
    st.info(
        "Используйте меню слева для перехода к разделам: ремонт, счётчики, дефекты, отчёты и прогнозы."
    )
