# -*- coding: utf-8 -*-
from __future__ import annotations

import requests
import streamlit as st

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

# Авторизация
token = st.sidebar.text_input("Токен доступа", type="password")

def get_headers() -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


st.set_page_config(page_title="Ремонтные работы", page_icon="🛠️", layout="wide")
st.title("Ремонтные работы")
st.caption("Журнал заявок и статистика")


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
        resp = requests.get(f"{API_BASE_URL}/repair/stats/summary", timeout=5, headers=get_headers())
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
def fetch_repair_types() -> list:
    return fetch_list("/repair/types")


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

st.subheader("Новая заявка")
buildings = fetch_buildings()
building_options = {f"{b.get('name')} (ID {b.get('id')})": b.get("id") for b in buildings}

with st.form("create_repair_request", clear_on_submit=True):
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

    types = fetch_repair_types()
    type_options = {f"{t.get('name')} (ID {t.get('id')})": t.get("id") for t in types}
    type_label = st.selectbox(
        "Тип работ",
        options=list(type_options.keys()) if type_options else [],
    )
    repair_type_id = type_options.get(type_label) if type_options else None

    title = st.text_input("Заголовок", max_chars=200)
    description = st.text_area("Описание", height=120)
    priority = st.selectbox("Приоритет", ["low", "medium", "high", "critical"], index=1)
    scheduled_date = st.date_input("Дата выполнения", value=None)

    submitted = st.form_submit_button("Создать заявку")
    if submitted:
        if not premise_id:
            st.error("Выберите помещение.")
        elif not title or not description:
            st.error("Заполните заголовок и описание.")
        else:
            payload = {
                "premise_id": premise_id,
                "repair_type_id": repair_type_id,
                "title": title.strip(),
                "description": description.strip(),
                "priority": priority,
                "scheduled_date": str(scheduled_date) if scheduled_date else None,
            }
            try:
                resp = requests.post(
                    f"{API_BASE_URL}/repair/requests",
                    json=payload,
                    timeout=5,
                    headers=get_headers(),
                )
                if resp.status_code in (200, 201):
                    st.success("Заявка создана")
                    st.rerun()
                else:
                    st.error(f"Ошибка: {resp.status_code} — {resp.text}")
            except Exception as exc:
                st.error(f"Ошибка запроса: {exc}")

st.divider()

st.subheader("Список заявок")
requests_list = fetch_list("/repair/requests")
if requests_list:
    st.dataframe(requests_list, use_container_width=True)
else:
    st.info("Данные не найдены.")
