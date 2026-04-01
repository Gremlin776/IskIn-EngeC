# -*- coding: utf-8 -*-
"""
Seeder для заполнения БД тестовыми данными
"""

import asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.core.database import AsyncSessionLocal, engine, Base
from src.models.user import User
from src.models.building import Building, Premise
from src.models.repair import RepairType, RepairRequest
from src.models.meter import MeterType, Meter, MeterReading
from src.models.defect import DefectClass


class Seeder:
    """Класс для заполнения БД тестовыми данными"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.created_count: dict[str, int] = {}
        self.skipped_count: dict[str, int] = {}

    async def _exists(self, model: type, **filters) -> bool:
        """Проверка существования записи"""
        stmt = select(func.count()).select_from(model)
        for key, value in filters.items():
            stmt = stmt.where(getattr(model, key) == value)
        result = await self.session.execute(stmt)
        return result.scalar() > 0

    async def _get_or_create(self, model: type, data: dict[str, Any], unique_fields: list[str] | str = None) -> Any:
        """Получение существующей записи или создание новой"""
        # Определяем уникальные поля для поиска
        if unique_fields is None:
            priority_fields = ["code", "meter_number", "request_number",
                               "inspection_number", "username", "email", "name"]
            for field in priority_fields:
                if field in data:
                    unique_fields = [field]
                    break

        if unique_fields:
            if isinstance(unique_fields, str):
                unique_fields = [unique_fields]

            # Пытаемся найти существующую запись по уникальным полям
            filters = [getattr(model, field) == data[field]
                       for field in unique_fields if field in data]
            if filters:
                stmt = select(model).where(*filters)
                result = await self.session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    self.skipped_count[model.__tablename__] = \
                        self.skipped_count.get(model.__tablename__, 0) + 1
                    return existing

        # Создаём новую запись
        instance = model(**data)
        self.session.add(instance)
        await self.session.flush()

        self.created_count[model.__tablename__] = \
            self.created_count.get(model.__tablename__, 0) + 1

        return instance

    async def _get_by_field(self, model: type, field: str, value: Any) -> Any | None:
        """Получение записи по полю"""
        stmt = select(model).where(getattr(model, field) == value)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def seed_users(self) -> dict[str, User]:
        """Создание тестовых пользователей"""
        users_data = [
            {
                "username": "admin",
                "email": "admin@iskin.local",
                "password_hash": "pbkdf2_sha256$600000$admin_salt$admin_hash_placeholder",
                "full_name": "Администратор Системы",
                "role": "admin",
                "is_active": True,
            },
            {
                "username": "engineer1",
                "email": "engineer1@iskin.local",
                "password_hash": "pbkdf2_sha256$600000$engineer_salt$engineer_hash_placeholder",
                "full_name": "Петров Иван Сергеевич",
                "role": "engineer",
                "is_active": True,
            },
            {
                "username": "user1",
                "email": "user1@iskin.local",
                "password_hash": "pbkdf2_sha256$600000$user_salt$user_hash_placeholder",
                "full_name": "Сидорова Анна Михайловна",
                "role": "user",
                "is_active": True,
            },
        ]

        users = {}
        for user_data in users_data:
            user = await self._get_or_create(User, user_data, "username")
            if user:
                users[user_data["username"]] = user

        return users

    async def seed_buildings(self) -> list[Building]:
        """Создание зданий с реальными адресами Москвы"""
        buildings_data = [
            {
                "name": "Административный корпус №1",
                "address": "г. Москва, ул. Тверская, д. 15",
                "building_type": "административное",
                "year_built": 1965,
                "floors": 12,
                "total_area": Decimal("4500.00"),
                "is_active": True,
            },
            {
                "name": "Технический центр",
                "address": "г. Москва, Ленинский проспект, д. 32",
                "building_type": "технический",
                "year_built": 1978,
                "floors": 5,
                "total_area": Decimal("2800.00"),
                "is_active": True,
            },
            {
                "name": "Складской комплекс",
                "address": "г. Москва, Варшавское шоссе, д. 47, стр. 3",
                "building_type": "складской",
                "year_built": 1985,
                "floors": 3,
                "total_area": Decimal("6200.00"),
                "is_active": True,
            },
        ]

        buildings = []
        for building_data in buildings_data:
            building = await self._get_or_create(Building, building_data, "name")
            if building:
                buildings.append(building)

        return buildings

    async def seed_premises(self, buildings: list[Building]) -> list[Premise]:
        """Создание помещений для зданий"""
        # Если здания не переданы, получаем существующие
        if not buildings:
            stmt = select(Building).order_by(Building.id)
            result = await self.session.execute(stmt)
            buildings = list(result.scalars().all())

        premises_data = [
            # Здание 1 - Административный корпус
            {"building_id": buildings[0].id, "floor": 1, "room_number": "101",
             "room_name": "Приёмная", "room_type": "офис", "area": Decimal("25.50")},
            {"building_id": buildings[0].id, "floor": 1, "room_number": "102",
             "room_name": "Переговорная", "room_type": "офис", "area": Decimal("35.00")},
            {"building_id": buildings[0].id, "floor": 2, "room_number": "201",
             "room_name": "Бухгалтерия", "room_type": "офис", "area": Decimal("42.00")},

            # Здание 2 - Технический центр
            {"building_id": buildings[1].id, "floor": 1, "room_number": "Т1-01",
             "room_name": "Серверная", "room_type": "техническое", "area": Decimal("30.00")},
            {"building_id": buildings[1].id, "floor": 1, "room_number": "Т1-02",
             "room_name": "Электрощитовая", "room_type": "техническое", "area": Decimal("22.00")},

            # Здание 3 - Складской комплекс
            {"building_id": buildings[2].id, "floor": 1, "room_number": "С1-01",
             "room_name": "Склад материалов", "room_type": "склад", "area": Decimal("150.00")},
            {"building_id": buildings[2].id, "floor": 1, "room_number": "С1-02",
             "room_name": "Зона погрузки", "room_type": "склад", "area": Decimal("80.00")},
        ]

        premises = []
        for premise_data in premises_data:
            # Проверяем по уникальному сочетанию building_id + floor + room_number
            premise = await self._get_or_create(
                Premise,
                premise_data,
                unique_fields=["building_id", "floor", "room_number"]
            )
            if premise:
                premises.append(premise)

        return premises


# Совместимость с ожидаемым именем в проверке

    async def seed_repair_types(self) -> list[RepairType]:
        """Создание типов ремонтных работ"""
        repair_types_data = [
            {
                "name": "Замена электропроводки",
                "code": "ELEC-001",
                "description": "Полная или частичная замена электрической проводки",
                "priority": 1,
            },
            {
                "name": "Устранение протечек",
                "code": "PLUMB-001",
                "description": "Локализация и устранение протечек водоснабжения и канализации",
                "priority": 2,
            },
            {
                "name": "Ремонт оконных конструкций",
                "code": "WINDOW-001",
                "description": "Регулировка, замена уплотнителей, ремонт фурнитуры окон",
                "priority": 3,
            },
            {
                "name": "Восстановление отделки",
                "code": "FINISH-001",
                "description": "Штукатурные работы, покраска, оклейка обоями",
                "priority": 4,
            },
            {
                "name": "Ремонт систем вентиляции",
                "code": "VENT-001",
                "description": "Обслуживание и ремонт систем приточно-вытяжной вентиляции",
                "priority": 2,
            },
        ]

        repair_types = []
        for rt_data in repair_types_data:
            rt = await self._get_or_create(RepairType, rt_data, "code")
            if rt:
                repair_types.append(rt)

        return repair_types

    async def seed_repair_requests(
        self,
        premises: list[Premise],
        users: dict[str, User],
        repair_types: list[RepairType]
    ) -> list[RepairRequest]:
        """Создание заявок на ремонт"""
        # Если данные не переданы, получаем существующие
        if not premises:
            stmt = select(Premise).order_by(Premise.id)
            result = await self.session.execute(stmt)
            premises = list(result.scalars().all())

        if not users:
            users = {}
            for username in ["admin", "engineer1", "user1"]:
                user = await self._get_by_field(User, "username", username)
                if user:
                    users[username] = user

        if not repair_types:
            stmt = select(RepairType).order_by(RepairType.id)
            result = await self.session.execute(stmt)
            repair_types = list(result.scalars().all())

        today = date.today()

        requests_data = [
            {
                "request_number": "REQ-2025-001",
                "premise_id": premises[0].id,
                "user_id": users["user1"].id,
                "repair_type_id": repair_types[0].id,
                "title": "Не работает розетка в приёмной",
                "description": "В помещении 101 не функционирует двойная розетка у входа. Требуется диагностика и замена.",
                "status": "completed",
                "priority": "medium",
                "scheduled_date": today - timedelta(days=10),
                "completed_date": today - timedelta(days=8),
                "cost": Decimal("3500.00"),
                "notes": "Заменена розетка, проводка в порядке",
            },
            {
                "request_number": "REQ-2025-002",
                "premise_id": premises[1].id,
                "user_id": users["user1"].id,
                "repair_type_id": repair_types[1].id,
                "title": "Протечка трубы в переговорной",
                "description": "Обнаружена протечка трубы отопления под окном. Необходима срочная замена участка трубы.",
                "status": "in_progress",
                "priority": "high",
                "scheduled_date": today - timedelta(days=2),
                "completed_date": None,
                "cost": None,
                "notes": "Ожидание запчастей",
            },
            {
                "request_number": "REQ-2025-003",
                "premise_id": premises[2].id,
                "user_id": users["engineer1"].id,
                "repair_type_id": repair_types[2].id,
                "title": "Не закрывается окно в бухгалтерии",
                "description": "Сломана фурнитура окна, створка не прижимается. Требуется замена механизма.",
                "status": "new",
                "priority": "medium",
                "scheduled_date": today + timedelta(days=3),
                "completed_date": None,
                "cost": None,
                "notes": None,
            },
            {
                "request_number": "REQ-2025-004",
                "premise_id": premises[3].id,
                "user_id": users["engineer1"].id,
                "repair_type_id": repair_types[0].id,
                "title": "Искрение в электрощите серверной",
                "description": "При включении оборудования наблюдается искрение в главном электрощите. Критическая неисправность!",
                "status": "in_progress",
                "priority": "critical",
                "scheduled_date": today,
                "completed_date": None,
                "cost": None,
                "notes": "Вызван аварийный электрик",
            },
            {
                "request_number": "REQ-2025-005",
                "premise_id": premises[4].id,
                "user_id": users["user1"].id,
                "repair_type_id": repair_types[4].id,
                "title": "Шум в системе вентиляции",
                "description": "Посторонний шум при работе вентиляции в электрощитовой. Требуется диагностика вентилятора.",
                "status": "new",
                "priority": "low",
                "scheduled_date": today + timedelta(days=5),
                "completed_date": None,
                "cost": None,
                "notes": None,
            },
            {
                "request_number": "REQ-2025-006",
                "premise_id": premises[5].id,
                "user_id": users["user1"].id,
                "repair_type_id": repair_types[3].id,
                "title": "Повреждение штукатурки на складе",
                "description": "Обнаружены отслоения штукатурки на северной стене склада. Требуется восстановление.",
                "status": "completed",
                "priority": "low",
                "scheduled_date": today - timedelta(days=15),
                "completed_date": today - timedelta(days=12),
                "cost": Decimal("12000.00"),
                "notes": "Работы выполнены в полном объёме",
            },
            {
                "request_number": "REQ-2025-007",
                "premise_id": premises[6].id,
                "user_id": users["engineer1"].id,
                "repair_type_id": repair_types[1].id,
                "title": "Засор канализации в зоне погрузки",
                "description": "Плохо уходит вода в трапе зоны погрузки. Требуется прочистка канализации.",
                "status": "cancelled",
                "priority": "medium",
                "scheduled_date": today - timedelta(days=5),
                "completed_date": None,
                "cost": None,
                "notes": "Отменено: засор устранён самостоятельно",
            },
            {
                "request_number": "REQ-2025-008",
                "premise_id": premises[0].id,
                "user_id": users["user1"].id,
                "repair_type_id": repair_types[3].id,
                "title": "Покраска стен в приёмной",
                "description": "Плановая покраска стен в помещении приёмной. Обновление интерьера.",
                "status": "new",
                "priority": "low",
                "scheduled_date": today + timedelta(days=7),
                "completed_date": None,
                "cost": None,
                "notes": "Согласовать цвет с руководством",
            },
            {
                "request_number": "REQ-2025-009",
                "premise_id": premises[1].id,
                "user_id": users["engineer1"].id,
                "repair_type_id": repair_types[4].id,
                "title": "Замена фильтров вентиляции",
                "description": "Плановая замена воздушных фильтров в системе вентиляции переговорной.",
                "status": "completed",
                "priority": "medium",
                "scheduled_date": today - timedelta(days=3),
                "completed_date": today - timedelta(days=3),
                "cost": Decimal("2500.00"),
                "notes": "Фильтры заменены, система протестирована",
            },
            {
                "request_number": "REQ-2025-010",
                "premise_id": premises[2].id,
                "user_id": users["user1"].id,
                "repair_type_id": repair_types[0].id,
                "title": "Мерцание света в бухгалтерии",
                "description": "Периодическое мерцание потолочных светильников. Возможна проблема с проводкой или контактами.",
                "status": "new",
                "priority": "medium",
                "scheduled_date": today + timedelta(days=2),
                "completed_date": None,
                "cost": None,
                "notes": None,
            },
        ]

        requests = []
        for req_data in requests_data:
            req = await self._get_or_create(RepairRequest, req_data, "request_number")
            if req:
                requests.append(req)

        return requests

    async def seed_meter_types(self) -> dict[str, MeterType]:
        """Создание типов счётчиков"""
        meter_types_data = [
            {
                "name": "Холодная вода",
                "code": "WATER_COLD",
                "unit": "м³",
                "icon": "water-drop",
            },
            {
                "name": "Горячая вода",
                "code": "WATER_HOT",
                "unit": "м³",
                "icon": "water-drop-hot",
            },
            {
                "name": "Электроэнергия",
                "code": "ELECTRICITY",
                "unit": "кВт·ч",
                "icon": "lightning",
            },
            {
                "name": "Природный газ",
                "code": "GAS",
                "unit": "м³",
                "icon": "fire",
            },
        ]

        meter_types = {}
        for mt_data in meter_types_data:
            mt = await self._get_or_create(MeterType, mt_data, "code")
            if mt:
                meter_types[mt_data["code"]] = mt

        return meter_types

    async def seed_meters(
        self,
        premises: list[Premise],
        meter_types: dict[str, MeterType]
    ) -> list[Meter]:
        """Создание счётчиков с показаниями"""
        # Если данные не переданы, получаем существующие
        if not premises:
            stmt = select(Premise).order_by(Premise.id)
            result = await self.session.execute(stmt)
            premises = list(result.scalars().all())

        if not meter_types:
            stmt = select(MeterType).order_by(MeterType.id)
            result = await self.session.execute(stmt)
            meter_types = {mt.code: mt for mt in result.scalars().all()}

        today = date.today()

        meters_data = [
            {
                "meter_number": "WC-101-001",
                "premise_id": premises[0].id,
                "meter_type_id": meter_types["WATER_COLD"].id,
                "manufacturer": "Valtec",
                "model": "VLF-15",
                "serial_number": "SN2023001",
                "install_date": today - timedelta(days=730),
                "verification_date": today - timedelta(days=365),
                "next_verification": today + timedelta(days=365),
                "is_active": True,
            },
            {
                "meter_number": "E-101-001",
                "premise_id": premises[0].id,
                "meter_type_id": meter_types["ELECTRICITY"].id,
                "manufacturer": "Энергомера",
                "model": "CE101",
                "serial_number": "SN2022045",
                "install_date": today - timedelta(days=1095),
                "verification_date": today - timedelta(days=365),
                "next_verification": today + timedelta(days=365),
                "is_active": True,
            },
            {
                "meter_number": "WH-T102-001",
                "premise_id": premises[1].id,
                "meter_type_id": meter_types["WATER_HOT"].id,
                "manufacturer": "Betar",
                "model": "СГВ-15",
                "serial_number": "SN2023112",
                "install_date": today - timedelta(days=400),
                "verification_date": today - timedelta(days=30),
                "next_verification": today + timedelta(days=335),
                "is_active": True,
            },
            {
                "meter_number": "E-T103-001",
                "premise_id": premises[2].id,
                "meter_type_id": meter_types["ELECTRICITY"].id,
                "manufacturer": "Меркурий",
                "model": "201.5",
                "serial_number": "SN2021089",
                "install_date": today - timedelta(days=1500),
                "verification_date": today - timedelta(days=100),
                "next_verification": today + timedelta(days=265),
                "is_active": True,
            },
            {
                "meter_number": "G-S101-001",
                "premise_id": premises[5].id,
                "meter_type_id": meter_types["GAS"].id,
                "manufacturer": "Бетар",
                "model": "СГБ-4",
                "serial_number": "SN2022067",
                "install_date": today - timedelta(days=800),
                "verification_date": today - timedelta(days=200),
                "next_verification": today + timedelta(days=165),
                "is_active": True,
            },
        ]

        meters = []
        for meter_data in meters_data:
            meter = await self._get_or_create(Meter, meter_data, "meter_number")
            if meter:
                meters.append(meter)

        return meters

    async def seed_meter_readings(self, meters: list[Meter]) -> list[MeterReading]:
        """Создание показаний счётчиков за 6 месяцев"""
        # Если счётчики не переданы, получаем существующие
        if not meters:
            stmt = select(Meter).order_by(Meter.id)
            result = await self.session.execute(stmt)
            meters = list(result.scalars().all())

        readings = []

        # Генерируем показания за 6 месяцев для каждого счётчика
        base_readings = {
            # WC-101-001
            0: {"start": Decimal("1250.500"), "increment": Decimal("3.200")},
            # E-101-001
            1: {"start": Decimal("4580.00"), "increment": Decimal("150.00")},
            # WH-T102-001
            2: {"start": Decimal("890.300"), "increment": Decimal("2.100")},
            # E-T103-001
            3: {"start": Decimal("8920.00"), "increment": Decimal("200.00")},
            # G-S101-001
            4: {"start": Decimal("456.700"), "increment": Decimal("12.500")},
        }

        for idx, meter in enumerate(meters):
            base = base_readings[idx]
            current_value = base["start"]

            for month in range(6, 0, -1):
                reading_date = date.today().replace(day=25) - timedelta(days=30 * month)
                current_value += base["increment"]

                reading_data = {
                    "meter_id": meter.id,
                    "reading_value": current_value,
                    "reading_date": reading_date,
                    "is_verified": month < 5,  # Последние 2 месяца не верифицированы
                    "source": "manual",
                }

                reading = await self._get_or_create(
                    MeterReading,
                    reading_data,
                    unique_fields=["meter_id", "reading_date"]
                )
                if reading:
                    readings.append(reading)

        return readings

    async def seed_defect_classes(self) -> list[DefectClass]:
        """Создание классов дефектов"""
        defect_classes_data = [
            {
                "name": "Трещина",
                "code": "CRACK",
                "yolo_class_id": 0,
                "description": "Трещины различной глубины и протяжённости в конструкциях",
                "severity_level": 3,
                "color": "#FF5733",
            },
            {
                "name": "Протечка",
                "code": "LEAK",
                "yolo_class_id": 1,
                "description": "Протечки воды, следы увлажнения конструкций",
                "severity_level": 4,
                "color": "#33C1FF",
            },
            {
                "name": "Коррозия",
                "code": "CORROSION",
                "yolo_class_id": 2,
                "description": "Коррозионные повреждения металлических элементов",
                "severity_level": 3,
                "color": "#8B4513",
            },
        ]

        defect_classes = []
        for dc_data in defect_classes_data:
            dc = await self._get_or_create(DefectClass, dc_data, "code")
            if dc:
                defect_classes.append(dc)

        return defect_classes

    async def run(self) -> dict[str, dict[str, int]]:
        """Запуск seeder"""
        print("🌱 Запуск seeder для заполнения БД тестовыми данными...")
        print("-" * 60)

        # Пользователи
        print("👤 Создание пользователей...")
        users = await self.seed_users()
        print(
            f"   Создано: {len(users)}, Пропущено: {self.skipped_count.get('users', 0)}")

        # Здания
        print("🏢 Создание зданий...")
        buildings = await self.seed_buildings()
        print(
            f"   Создано: {len(buildings)}, Пропущено: {self.skipped_count.get('buildings', 0)}")

        # Помещения
        print("🚪 Создание помещений...")
        premises = await self.seed_premises(buildings)
        print(
            f"   Создано: {len(premises)}, Пропущено: {self.skipped_count.get('premises', 0)}")

        # Типы ремонтов
        print("🔧 Создание типов ремонтных работ...")
        repair_types = await self.seed_repair_types()
        print(
            f"   Создано: {len(repair_types)}, Пропущено: {self.skipped_count.get('repair_types', 0)}")

        # Заявки на ремонт
        print("📋 Создание заявок на ремонт...")
        repair_requests = await self.seed_repair_requests(premises, users, repair_types)
        print(
            f"   Создано: {len(repair_requests)}, Пропущено: {self.skipped_count.get('repair_requests', 0)}")

        # Типы счётчиков
        print("📊 Создание типов счётчиков...")
        meter_types = await self.seed_meter_types()
        print(
            f"   Создано: {len(meter_types)}, Пропущено: {self.skipped_count.get('meter_types', 0)}")

        # Счётчики
        print("💧 Создание счётчиков...")
        meters = await self.seed_meters(premises, meter_types)
        print(
            f"   Создано: {len(meters)}, Пропущено: {self.skipped_count.get('meters', 0)}")

        # Показания счётчиков
        print("📈 Создание показаний счётчиков...")
        readings = await self.seed_meter_readings(meters)
        print(
            f"   Создано: {len(readings)}, Пропущено: {self.skipped_count.get('meter_readings', 0)}")

        # Классы дефектов
        print("⚠️  Создание классов дефектов...")
        defect_classes = await self.seed_defect_classes()
        print(
            f"   Создано: {len(defect_classes)}, Пропущено: {self.skipped_count.get('defect_classes', 0)}")

        # Фиксация транзакции в базе данных
        await self.session.commit()

        print("-" * 60)
        print("✅ Seeder завершён успешно!")
        print()
        print("📊 Итого создано:")
        for table, count in self.created_count.items():
            print(f"   • {table}: {count}")

        if any(self.skipped_count.values()):
            print()
            print("⏭️  Пропущено (уже существуют):")
            for table, count in self.skipped_count.items():
                if count > 0:
                    print(f"   • {table}: {count}")
        print()

        return {
            "created": self.created_count,
            "skipped": self.skipped_count,
        }


async def seed_database():
    """Точка входа для запуска seeder"""
    async with AsyncSessionLocal() as session:
        seeder = Seeder(session)
        result = await seeder.run()
        return result


async def main():
    """Основная функция"""
    try:
        await seed_database()
    except Exception as e:
        print(f"❌ Ошибка при выполнении seeder: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

DatabaseSeeder = Seeder
