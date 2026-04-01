# -*- coding: utf-8 -*-
"""
LLM client для генерации отчётов.

Поддерживает:
- OpenAI API (если есть ключ)
- Ollama локальная (если установлена)
- Резервный сценарий: шаблонная генерация без LLM
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import httpx

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class LLMClient:
    """Клиент для генерации отчётов через LLM."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._ollama_url = "http://localhost:11434/api/generate"
        self._anthropic_url = "https://api.anthropic.com/v1/messages"

    async def generate_report(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """
        Генерация текста отчёта.

        Приоритеты:
        1. OpenAI API (если есть ключ)
        2. Ollama локальная (если доступна)
        3. Шаблонная генерация (fallback)
        """
        # 1. Пробуем OpenAI
        if self.settings.llm_api_key and self.settings.llm_api_key.strip():
            try:
                return await self._generate_openai(prompt)
            except Exception as e:
                logger.warning(f"OpenAI API ошибка: {e}, пробуем fallback")

        # 2. Пробуем Ollama локальную
        try:
            return await self._generate_ollama(prompt)
        except Exception:
            pass

        # 3. Резервный сценарий: шаблонная генерация
        logger.info("Использую шаблонную генерацию отчёта")
        return self._generate_template(prompt, context or {})

    async def _generate_openai(self, prompt: str) -> str:
        """Генерация через OpenAI API."""
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.settings.llm_model or "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "Вы помощник для генерации отчётов по эксплуатации зданий. Отвечайте кратко, по делу, на русском языке.",
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1500,
            "temperature": 0.7,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.settings.llm_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def _generate_ollama(self, prompt: str) -> str:
        """Генерация через локальную Ollama."""
        payload = {
            "model": "llama3.2",
            "prompt": prompt,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self._ollama_url,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

    def _generate_template(
        self,
        prompt: str,
        context: dict[str, Any],
    ) -> str:
        """
        Шаблонная генерация отчёта без LLM.

        Создаёт структурированный отчёт на основе контекста.
        """
        now = datetime.now().strftime("%d.%m.%Y %H:%M")

        # Извлекаем данные из контекста
        building_name = context.get("building_name", "Не указано")
        premise_count = context.get("premise_count", 0)
        repair_requests = context.get("repair_requests", [])
        meters = context.get("meters", [])
        defects = context.get("defects", [])
        period_start = context.get("period_start", "01.01.2025")
        period_end = context.get(
            "period_end", datetime.now().strftime("%d.%m.%Y"))

        # Формируем отчёт
        report_lines = [
            "# ОТЧЁТ ПО ЭКСПЛУАТАЦИИ ЗДАНИЯ",
            "",
            f"**Дата формирования:** {now}",
            f"**Период:** {period_start} — {period_end}",
            "",
            "## 1. ОБЩАЯ ИНФОРМАЦИЯ",
            "",
            f"- **Здание:** {building_name}",
            f"- **Количество помещений:** {premise_count}",
            "",
            "## 2. РЕМОНТНЫЕ РАБОТЫ",
            "",
        ]

        if repair_requests:
            report_lines.append(f"Всего заявок: {len(repair_requests)}")
            report_lines.append("")

            # Группировка по статусам
            status_counts: dict[str, int] = {}
            for req in repair_requests:
                status = req.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1

            status_names = {
                "new": "Новые",
                "in_progress": "В работе",
                "completed": "Завершённые",
                "cancelled": "Отменённые",
            }

            for status, count in status_counts.items():
                name = status_names.get(status, status)
                report_lines.append(f"- {name}: {count}")

            report_lines.append("")

            # Последние заявки
            if repair_requests:
                report_lines.append("### Последние заявки:")
                report_lines.append("")
                for req in repair_requests[:5]:
                    report_lines.append(
                        f"- **{req.get('request_number', 'N/A')}**: {req.get('title', 'Без названия')} "
                        f"(статус: {status_names.get(req.get('status'), req.get('status'))})"
                    )
                report_lines.append("")
        else:
            report_lines.append("Ремонтные работы не проводились.")
            report_lines.append("")

        # Счётчики
        report_lines.append("## 3. ПОКАЗАНИЯ СЧЁТЧИКОВ")
        report_lines.append("")

        if meters:
            report_lines.append("| Номер | Тип | Последнее показание | Дата |")
            report_lines.append("|-------|-----|---------------------|------|")
            for meter in meters[:10]:
                report_lines.append(
                    f"| {meter.get('meter_number', 'N/A')} | "
                    f"{meter.get('type_name', 'N/A')} | "
                    f"{meter.get('last_value', 'N/A')} {meter.get('unit', '')} | "
                    f"{meter.get('last_date', 'N/A')} |"
                )
            report_lines.append("")
        else:
            report_lines.append("Данные счётчиков отсутствуют.")
            report_lines.append("")

        # Дефекты
        report_lines.append("## 4. ДЕФЕКТЫ И ПОВРЕЖДЕНИЯ")
        report_lines.append("")

        if defects:
            report_lines.append(f"Всего обнаружено дефектов: {len(defects)}")
            report_lines.append("")

            # Группировка по типам
            defect_types: dict[str, int] = {}
            for defect in defects:
                defect_type = defect.get("class_name", "unknown")
                defect_types[defect_type] = defect_types.get(
                    defect_type, 0) + 1

            report_lines.append("### По типам:")
            for dtype, count in defect_types.items():
                report_lines.append(f"- {dtype}: {count}")
            report_lines.append("")
        else:
            report_lines.append("Дефекты не обнаружены.")
            report_lines.append("")

        # Рекомендации
        report_lines.append("## 5. РЕКОМЕНДАЦИИ")
        report_lines.append("")

        recommendations = []

        # Анализ заявок
        in_progress = sum(1 for r in repair_requests if r.get(
            "status") == "in_progress")
        if in_progress > 0:
            recommendations.append(
                f"⚠️ В работе {in_progress} заявок — рекомендуется контролировать сроки выполнения"
            )

        new_requests = sum(
            1 for r in repair_requests if r.get("status") == "new")
        if new_requests > 0:
            recommendations.append(
                f"📋 {new_requests} новых заявок ожидают назначения исполнителя"
            )

        # Анализ дефектов
        critical_defects = sum(
            1 for d in defects if d.get("severity") in ["critical", "high"]
        )
        if critical_defects > 0:
            recommendations.append(
                f"🔴 Обнаружено {critical_defects} критических дефектов — требуется срочное вмешательство"
            )

        if not recommendations:
            recommendations.append("✅ Критических проблем не выявлено")
            recommendations.append(
                "📅 Рекомендуется плановое обслуживание согласно графику")

        for rec in recommendations:
            report_lines.append(f"- {rec}")

        report_lines.append("")
        report_lines.append("---")
        report_lines.append(
            "*Отчёт сформирован автоматически системой «Инженерный ИскИн»*")

        return "\n".join(report_lines)

    async def analyze_defects(self, defects_data: list[dict[str, Any]]) -> str:
        """Анализ дефектов и рекомендации."""
        prompt = f"""
Проанализируй данные дефекты и дай рекомендации:

{defects_data}

Дай краткий анализ на русском языке:
1. Основные проблемы
2. Рекомендации по устранению
3. Приоритеты работ
"""
        return await self.generate_report(prompt, {"defects": defects_data})

    async def summarize_readings(
        self,
        readings_data: list[dict[str, Any]],
        meter_type: str,
    ) -> str:
        """Суммаризация показаний счётчиков."""
        prompt = f"""
Проанализируй показания счётчиков ({meter_type}) и выяви аномалии:

{readings_data}

Дай краткий анализ на русском языке:
1. Динамика потребления
2. Выявленные аномалии
3. Рекомендации
"""
        return await self.generate_report(prompt, {"readings": readings_data})
