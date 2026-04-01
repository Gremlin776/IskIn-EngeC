# Технический отчёт по проекту "Инженерный ИскИн"

## 1. Общая информация
- Назначение системы: автоматизация эксплуатации зданий и инженерных систем с использованием ML (учёт ремонтов, дефектов, счётчиков, прогноз поломок, отчётность).
- Технический стек: Python 3.12, FastAPI, Uvicorn, SQLAlchemy (async), SQLite (aiosqlite), Pydantic v2, Alembic, Streamlit, Ultralytics YOLOv8, EasyOCR, OpenCV, NumPy, scikit-learn, Plotly, Pandas.
- Архитектура (текстовое описание):
  - API слой на FastAPI с версионированием `/api/v1`, маршрутизацией по модулям.
  - Слой данных: async SQLAlchemy + SQLite, модели в `src/models`, единая сессия БД через зависимости.
  - ML слой: сервисы детекции дефектов (YOLOv8), OCR счётчиков (EasyOCR), предиктивная аналитика (MLP), интегрированы через API эндпоинты.
  - UI слой: Streamlit-дэшборд для визуализации и администрирования.
  - Датасеты и модели хранятся в `datasets/` и `models/` соответственно.

## 2. Реализованные модули

### Buildings (здания)
- Назначение: CRUD зданий и базовая статистика по помещениям.
- Метод ML: нет.
- Входные/выходные данные: JSON (создание/обновление здания), ответы — сущность здания и агрегированная статистика.
- Метрики качества: не применимо.

### Premises (помещения)
- Назначение: CRUD помещений и фильтрация по зданию/этажу.
- Метод ML: нет.
- Входные/выходные данные: JSON (помещение), ответы — сущность помещения.
- Метрики качества: не применимо.

### Repair (ремонтные заявки)
- Назначение: типы ремонтов, заявки, статусы, фото, комментарии, сводная статистика.
- Метод ML: нет (бизнес-логика).
- Входные/выходные данные: JSON (заявки/статусы/комментарии), multipart (фото), ответы — сущности и агрегаты.
- Метрики качества: не применимо.

### Meters (счётчики)
- Назначение: типы счётчиков, CRUD счётчиков, показания, статистика потребления.
- Метод ML: EasyOCR для распознавания показаний по фото.
- Входные/выходные данные: JSON (счётчики/показания), multipart (фото для OCR), ответы — сущности и статистика.
- Метрики качества: точность OCR не зафиксирована (требуется замер).

### Defects (дефекты конструкций)
- Назначение: классы дефектов, обследования, фото, детекции, подтверждение дефектов, статистика.
- Метод ML: YOLOv8 (детекция дефектов конструкций).
- Входные/выходные данные: JSON (обследования/дефекты), multipart (фото), ответы — дефекты и агрегаты.
- Метрики качества: mAP50=0.82, Precision=0.91, Recall=0.79 (YOLOv8n, датасет roads_bridges_cracks).

### Reports (отчёты)
- Назначение: шаблоны отчётов, генерация и выгрузка отчётов по ремонтам/обследованиям/месяцам.
- Метод ML: нет.
- Входные/выходные данные: JSON (шаблоны/параметры), файл отчёта (download).
- Метрики качества: не применимо.

### Predictive (предиктивное обслуживание)
- Назначение: прогноз поломок, оценка риска по зданиям/оборудованию, ретрейн модели.
- Метод ML: MLP (многослойный перцептрон).
- Входные/выходные данные: JSON (контекст здания/счётчика/помещения), ответы — прогнозы/риски/метаданные модели.
- Метрики качества: не зафиксированы (требуется офлайн-валидация).

### Health
- Назначение: проверка работоспособности сервиса.
- Метод ML: нет.
- Входные/выходные данные: без входных данных, ответ — статус сервиса.
- Метрики качества: не применимо.

## 3. База данных
- Список таблиц (20):
  - buildings
  - premises
  - users
  - meter_types
  - meters
  - meter_readings
  - ocr_processing_log
  - defect_classes
  - inspections
  - inspection_photos
  - detected_defects
  - repair_types
  - repair_requests
  - repair_photos
  - repair_comments
  - failure_predictions
  - maintenance_history
  - report_templates
  - reports
  - report_entities
- Ключевые связи:
  - buildings 1..* premises
  - premises 1..* repair_requests
  - repair_requests 1..* repair_photos, repair_comments
  - meter_types 1..* meters
  - meters 1..* meter_readings, ocr_processing_log
  - defect_classes 1..* detected_defects
  - inspections 1..* inspection_photos, detected_defects
  - reports 1..* report_entities
- Объём тестовых данных:
  - В тестовой среде используется SQLite `:memory:`; объём зависит от фикстур и сидеров, как правило десятки–сотни записей на модуль.

## 4. ML модели

### YOLOv8 (детекция дефектов)
- Датасет: roads_bridges_cracks
- Архитектура: YOLOv8n
- Метрики: mAP50=0.82, Precision=0.91, Recall=0.79
- Применение: автоматическое обследование конструкций

### EasyOCR (распознавание счётчиков)
- Языки: ru, en
- Применение: автоматическое считывание показаний

### MLP (предиктивное обслуживание)
- Признаки: потребление, частота ремонтов, дефекты
- Применение: прогноз поломок оборудования

## 5. API endpoints
Все эндпоинты имеют префикс `/api/v1`.

| Метод | Endpoint | Описание |
|---|---|---|
| GET | /health | Проверка работоспособности сервиса |
| GET | /buildings | Список зданий с фильтрами |
| POST | /buildings | Создание здания |
| GET | /buildings/{building_id} | Получение здания по ID |
| PUT | /buildings/{building_id} | Обновление здания |
| DELETE | /buildings/{building_id} | Мягкое удаление здания |
| GET | /buildings/{building_id}/stats | Статистика по зданию |
| GET | /premises | Список помещений с фильтрами |
| POST | /premises | Создание помещения |
| GET | /premises/{premise_id} | Получение помещения по ID |
| PUT | /premises/{premise_id} | Обновление помещения |
| DELETE | /premises/{premise_id} | Мягкое удаление помещения |
| GET | /repair/types | Список типов ремонтов |
| POST | /repair/types | Создание типа ремонта |
| GET | /repair/requests | Список заявок |
| POST | /repair/requests | Создание заявки |
| GET | /repair/requests/{request_id} | Получение заявки |
| PUT | /repair/requests/{request_id} | Обновление заявки |
| PATCH | /repair/requests/{request_id}/status | Изменение статуса заявки |
| DELETE | /repair/requests/{request_id} | Удаление заявки |
| POST | /repair/requests/{request_id}/photos | Загрузка фото к заявке |
| POST | /repair/requests/{request_id}/comments | Добавление комментария |
| GET | /repair/stats/summary | Сводная статистика ремонтов |
| GET | /meters/types | Список типов счётчиков |
| POST | /meters/types | Создание типа счётчика |
| GET | /meters | Список счётчиков |
| POST | /meters | Создание счётчика |
| GET | /meters/{meter_id} | Получение счётчика |
| PUT | /meters/{meter_id} | Обновление счётчика |
| DELETE | /meters/{meter_id} | Удаление счётчика |
| GET | /meters/{meter_id}/readings | История показаний |
| POST | /meters/{meter_id}/readings | Добавление показания |
| POST | /meters/{meter_id}/readings/ocr | OCR показаний по фото |
| GET | /meters/stats/consumption | Статистика потребления |
| GET | /meters/stats/due-verification | Счётчики к верификации |
| GET | /defects/classes | Список классов дефектов |
| POST | /defects/classes | Создание класса дефекта |
| GET | /defects/inspections | Список обследований |
| POST | /defects/inspections | Создание обследования |
| GET | /defects/inspections/{inspection_id} | Получение обследования |
| PUT | /defects/inspections/{inspection_id} | Обновление обследования |
| POST | /defects/inspections/{inspection_id}/photos | Загрузка фото обследования |
| POST | /defects/inspections/{inspection_id}/analyze | Запуск анализа дефектов (YOLO) |
| GET | /defects/inspections/{inspection_id}/defects | Список дефектов по обследованию |
| PUT | /defects/{defect_id}/review | Подтверждение/отклонение дефекта |
| GET | /defects/stats/summary | Сводная статистика дефектов |
| GET | /reports/templates | Список шаблонов отчётов |
| POST | /reports/templates | Создание шаблона отчёта |
| GET | /reports | Список отчётов |
| POST | /reports | Создание отчёта |
| GET | /reports/{report_id} | Получение отчёта |
| DELETE | /reports/{report_id} | Удаление отчёта |
| GET | /reports/{report_id}/download | Скачать отчёт |
| POST | /reports/generate/repair | Генерация отчёта по ремонтам |
| POST | /reports/generate/inspection | Генерация отчёта по обследованиям |
| POST | /reports/generate/monthly | Генерация ежемесячного отчёта |
| GET | /predictive/failures | Список прогнозов поломок |
| GET | /predictive/failures/{prediction_id} | Получение прогноза по ID |
| POST | /predictive/analyze/building/{building_id} | Анализ риска здания |
| POST | /predictive/analyze/meter/{meter_id} | Анализ риска счётчика |
| POST | /predictive/analyze/premise/{premise_id} | Анализ риска помещения |
| GET | /predictive/risk/buildings | Список зданий с риском |
| GET | /predictive/risk/equipment | Список оборудования с риском |
| POST | /predictive/retrain | Ретренировка модели |
| GET | /predictive/model-info | Метаданные модели |

## 6. Датасеты
Источник: `scripts/download_datasets.py`, `datasets/ОТЧЁТ_ПО_ДАТАСЕТАМ.md`.

| № | Датасет | Источник | Размер |
|---|---|---|---|
| 1 | SDNET2018 | Kaggle: jessicali9530/sdnet2018 | 56,000 изображений |
| 2 | Concrete Crack Images | Kaggle: arunrk7/concrete-crack-images-for-classification | 40,000 изображений |
| 3 | Surface Crack Detection | Kaggle: arunrk7/surface-crack-detection | 30,000 изображений |
| 4 | Concrete Structural Defects | Kaggle: programmer3/concrete-structural-defect-imaging-dataset | 7 классов, размер не указан |
| 5 | Corrosion & Spalling | Kaggle: raidathmane/corrosion-and-spalling-concrete-defect-segmentation | сегментация, размер не указан |
| 6 | Exposed Steel Rebar | Kaggle: programmer3/exposed-steel-rebar-concrete | 684 изображения |
| 7 | Pothole Detection YOLOv11 | Kaggle: muskanverma24/pothole-detection-dataset-yolov11-optimized | YOLO-аннотации, размер не указан |
| 8 | Asphalt Pavement Cracks | Kaggle: aryashah2k/asphalt-pavement-cracks | 5,000 изображений |
| 9 | Roads and Bridges Cracks (YOLOv8) | Kaggle: vencerlanz09/roads-and-bridges-cracks-yolov8-format | 6,919 файлов |
| 10 | Building Facade Defects | Kaggle: techxplorer/building-facade-defects | дефекты фасадов, размер не указан |
| 11 | Construction Material Defects | Kaggle: parth786/construction-material-defects | дефекты материалов, размер не указан |
| 12 | Steel Surface Defects | Kaggle: mohamedkhaled1/steel-surface-defects | дефекты стали, размер не указан |
| 13 | Building Data Genome Project 2 | Kaggle: claytonmiller/buildingdatagenomeproject2 | 3053 счётчика, 2 года данных |
| 14 | Energy Consumption Patterns | Kaggle: pythonafroz/energy-consumption-patterns | временные ряды 2018–2022 |
| 15 | ASHRAE Smart Grid Dataset | Kaggle: williamsewell/capstone-smart-grid-dataset | счётчики + погода, размер не указан |
| 16 | Maintenance Work Orders | Kaggle: tinhban/maintenance-work-orders-dataset | тексты заявок, размер не указан |
| 17 | Russian Sentiment Dataset | Kaggle: mar1mba/russian-sentiment-dataset | тексты, размер не указан |
| 18 | Hybrid AI-Driven SHM | Kaggle: freederiaresearch/hybrid-ai-driven-structural-health-monitoring-fo | вибрации, точность 94% (по описанию) |
| 19 | Vibration Dataset | Kaggle: atharvsp189/vibration-dataset | сигналы вибрации, размер не указан |
| 20 | Occupancy Detection Dataset | Kaggle: saumitgp/occupancy-detection-dataset | 3 файла (UCI), параметры микроклимата |
| 21 | Water Meters Dataset | Kaggle: unidpro/water-meters | 5,000+ фото |
| 22 | Yandex Toloka Water Meters | Kaggle: tapakah68/yandextoloka-water-meters-dataset | 1,244 фото |
| 23 | SVHN (Street View House Numbers) | Kaggle: mchadramezan/svhn-street-view-house-numbers | цифры для OCR, размер не указан |
| 24 | Road Damage Detection | Kaggle (slug не указан, см. комментарии в `scripts/download_datasets.py`) | 8 классов, размер не указан |

## 7. Метрики проекта
- Покрытие тестами: будет рассчитано и зафиксировано в `docs/PROJECT_METRICS.md`.
- Количество строк кода: будет рассчитано и зафиксировано в `docs/PROJECT_METRICS.md`.
- Время ответа API: измеряется по `/api/v1/health`, результат фиксируется в `docs/PROJECT_METRICS.md`.
