# -*- coding: utf-8 -*-
from __future__ import annotations

import requests
import streamlit as st

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

# Авторизация
token = st.sidebar.text_input("Токен доступа", type="password")

def get_headers() -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


st.set_page_config(page_title="Счётчики", page_icon="📟", layout="wide")
st.title("Счётчики")
st.caption("Учёт показаний и статистика")


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
def fetch_stats() -> dict:
    try:
        resp = requests.get(f"{API_BASE_URL}/meters/stats/consumption", timeout=5, headers=get_headers())
        if resp.status_code != 200:
            return {}
        return resp.json()
    except Exception:
        return {}


@st.cache_data(ttl=10)
def fetch_buildings() -> list:
    return fetch_list("/buildings")


@st.cache_data(ttl=10)
def fetch_premises(building_id: int | None) -> list:
    if building_id is None:
        return []
    try:
        resp = requests.get(
            f"{API_BASE_URL}/premises",
            params={"building_id": building_id},
            timeout=5,
            headers=get_headers(),
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


@st.cache_data(ttl=10)
def fetch_meter_types() -> list:
    return fetch_list("/meters/types")


stats = fetch_stats()
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Всего счётчиков", len(fetch_list("/meters")))
with col2:
    st.metric("Просрочена поверка", len(fetch_list("/meters/stats/due-verification")))
with col3:
    st.metric("Всего показаний", len(fetch_list("/meters")))

st.divider()

st.subheader("Добавить счётчик")
buildings = fetch_buildings()
building_options = {f"{b.get('name')} (ID {b.get('id')})": b.get("id") for b in buildings}

with st.form("create_meter", clear_on_submit=True):
    meter_number = st.text_input("Номер счётчика", max_chars=50)
    building_label = st.selectbox(
        "Здание",
        options=list(building_options.keys()) if building_options else [],
    )
    building_id = building_options.get(building_label) if building_options else None
    premises = fetch_premises(building_id)
    premise_options = {
        f"{p.get('room_number')} (этаж {p.get('floor')}, ID {p.get('id')})": p.get("id")
        for p in premises
    }
    premise_label = st.selectbox(
        "Помещение",
        options=list(premise_options.keys()) if premise_options else [],
    )
    premise_id = premise_options.get(premise_label) if premise_options else None

    types = fetch_meter_types()
    type_options = {f"{t.get('name')} ({t.get('unit')}) ID {t.get('id')}": t.get("id") for t in types}
    type_label = st.selectbox(
        "Тип счётчика",
        options=list(type_options.keys()) if type_options else [],
    )
    meter_type_id = type_options.get(type_label) if type_options else None

    submitted = st.form_submit_button("Добавить")
    if submitted:
        if not meter_number or not premise_id or not meter_type_id:
            st.error("Заполните номер счётчика, тип и помещение.")
        else:
            payload = {
                "meter_number": meter_number.strip(),
                "premise_id": premise_id,
                "meter_type_id": meter_type_id,
            }
            try:
                resp = requests.post(
                    f"{API_BASE_URL}/meters",
                    json=payload,
                    timeout=5,
                    headers=get_headers(),
                )
                if resp.status_code in (200, 201):
                    st.success("Счётчик добавлен")
                    st.rerun()
                else:
                    st.error(f"Ошибка: {resp.status_code} — {resp.text}")
            except Exception as exc:
                st.error(f"Ошибка запроса: {exc}")

st.subheader("Добавить показание вручную")
meters_list = fetch_list("/meters")
meter_options = {
    f"{m.get('meter_number')} (ID {m.get('id')})": m.get("id")
    for m in meters_list
}

with st.form("add_reading", clear_on_submit=True):
    meter_label = st.selectbox(
        "Счётчик",
        options=list(meter_options.keys()) if meter_options else [],
    )
    meter_id = meter_options.get(meter_label) if meter_options else None
    reading_value = st.number_input("Показание", min_value=0.0, value=0.0, step=0.1)
    reading_date = st.date_input("Дата показания")
    submitted_reading = st.form_submit_button("Добавить показание")

    if submitted_reading:
        if not meter_id:
            st.error("Выберите счётчик.")
        else:
            payload = {
                "reading_value": reading_value,
                "reading_date": str(reading_date),
            }
            try:
                resp = requests.post(
                    f"{API_BASE_URL}/meters/{meter_id}/readings",
                    json=payload,
                    timeout=5,
                    headers=get_headers(),
                )
                if resp.status_code in (200, 201):
                    st.success("Показание добавлено")
                    st.rerun()
                else:
                    st.error(f"Ошибка: {resp.status_code} — {resp.text}")
            except Exception as exc:
                st.error(f"Ошибка запроса: {exc}")

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
