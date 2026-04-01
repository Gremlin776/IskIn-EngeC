# Обучение YOLOv8 для детектирования трещин

## 📋 Обзор

Этот модуль предоставляет инструменты для обучения модели YOLOv8 на датасетах трещин в бетоне.

**Возможности:**
- Автоматическое скачивание датасетов с Kaggle
- Fine-tuning YOLOv8 (nano/small/medium)
- Inference на тестовых изображениях
- Визуализация метрик (mAP, Precision, Recall)

---

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -e ".[dev]"
pip install kaggle  # Для скачивания датасетов
```

### 2. Настройка Kaggle API

1. Зайдите на https://www.kaggle.com/account
2. Создайте новый API Token
3. Скачайте файл `kaggle.json`
4. Поместите его в `~/.kaggle/kaggle.json` (Linux/Mac) или `C:\Users\<You>\.kaggle\kaggle.json` (Windows)
5. Установите права доступа (Linux/Mac):
   ```bash
   chmod 600 ~/.kaggle/kaggle.json
   ```

**Альтернативно:** установите переменные окружения:
```bash
export KAGGLE_USERNAME=your_username
export KAGGLE_KEY=your_api_key
```

### 3. Скачивание датасетов

```bash
python scripts/download_datasets.py
```

**Что делает скрипт:**
- Скачивает SDNET2018 (трещины в бетоне)
- Скачивает Concrete Crack Images
- Создает структуру для YOLOv8 (train/val/test)
- Генерирует YAML-конфигурацию

**Структура после скачивания:**
```
datasets/defects/
├── sdnet2018/
│   ├── raw/              # Исходный архив
│   ├── extracted/        # Распакованные данные
│   ├── yolo/             # Структура для YOLOv8
│   │   ├── images/
│   │   │   ├── train/
│   │   │   ├── val/
│   │   │   └── test/
│   │   └── labels/
│   │       ├── train/
│   │       ├── val/
│   │       └── test/
│   └── dataset.yaml      # Конфигурация
└── concrete_crack/
    └── ...
```

### 4. Обучение модели

```bash
# Базовое обучение YOLOv8n (nano)
python scripts/train_yolo.py --dataset sdnet2018 --epochs 100 --batch 16

# Обучение с большими параметрами
python scripts/train_yolo.py --dataset sdnet2018 --model yolov8s.pt --epochs 200 --batch 32

# Только inference (без обучения)
python scripts/train_yolo.py --dataset sdnet2018 --inference-only
```

**Параметры командной строки:**
| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `--dataset` | Датасет (sdnet2018 / concrete_crack) | sdnet2018 |
| `--model` | Модель YOLOv8 | yolov8n.pt |
| `--epochs` | Количество эпох | 100 |
| `--batch` | Размер батча | 16 |
| `--img-size` | Размер изображения | 640 |
| `--device` | Устройство (cuda/cpu/0) | auto |
| `--no-pretrained` | Не использовать предобученные веса | False |
| `--inference-only` | Только inference | False |

### 5. Запуск Jupyter Notebook

```bash
# Откройте ноутбук для интерактивной работы
jupyter notebook notebooks/02_yolo_training.ipynb
```

---

## 📊 Метрики

После обучения скрипт автоматически вычисляет:

| Метрика | Описание |
|---------|----------|
| **mAP@50** | Mean Average Precision при IoU=0.5 |
| **mAP@50-95** | Mean Average Precision при IoU=0.5:0.95 |
| **Precision** | Точность (TP / (TP + FP)) |
| **Recall** | Полнота (TP / (TP + FN)) |
| **Fitness** | Общая функция пригодности модели |

**Результаты сохраняются в:**
- `models/yolo/yolov8n/train_metrics.json` - метрики обучения
- `models/yolo/yolov8n/eval_metrics.json` - метрики оценки
- `models/yolo/yolov8n/weights/best.pt` - лучшая модель

---

## 🔧 Конфигурация

### YAML-файл датасета

```yaml
path: /absolute/path/to/datasets/defects/sdnet2018/yolo
train: images/train
val: images/val
test: images/test

names:
  0: crack
```

### Гиперпараметры для экспериментов

```bash
# Для быстрого тестирования
python scripts/train_yolo.py --epochs 10 --batch 8 --img-size 320

# Для продакшена
python scripts/train_yolo.py --model yolov8m.pt --epochs 300 --batch 32 --img-size 1280
```

---

## 📁 Структура проекта

```
D:\VKR\IskIn EngeC\
├── scripts/
│   ├── download_datasets.py    # Скачивание датасетов
│   └── train_yolo.py           # Обучение YOLOv8
├── notebooks/
│   └── 02_yolo_training.ipynb  # Inference и визуализация
├── datasets/
│   └── defects/
│       ├── sdnet2018/
│       └── concrete_crack/
├── models/
│   └── yolo/
│       └── yolov8n/
│           ├── weights/
│           ├── eval/
│           └── inference/
└── logs/
    └── yolo/
```

---

## 🐛 Решение проблем

### Ошибка аутентификации Kaggle
```
ValueError: Не удалось аутентифицироваться в Kaggle API
```
**Решение:** Убедитесь, что файл `kaggle.json` существует и содержит правильные учетные данные.

### CUDA out of memory
```
RuntimeError: CUDA out of memory
```
**Решение:** Уменьшите размер батча или изображения:
```bash
python scripts/train_yolo.py --batch 8 --img-size 320
```

### Датасет не найден
```
FileNotFoundError: datasets/defects/sdnet2018/dataset.yaml
```
**Решение:** Запустите скрипт скачивания:
```bash
python scripts/download_datasets.py
```

---

## 📚 Ссылки

- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [SDNET2018 Dataset](https://www.kaggle.com/datasets/jessicali9530/sdnet2018)
- [Kaggle API](https://github.com/Kaggle/kaggle-api)

---

## 📝 Примеры использования

### Inference на одном изображении

```python
from ultralytics import YOLO

model = YOLO('models/yolo/yolov8n/weights/best.pt')
results = model.predict('path/to/image.jpg', conf=0.25)

for result in results:
    boxes = result.boxes
    for box in boxes:
        print(f"Class: {box.cls[0]}, Confidence: {box.conf[0]:.2f}")
```

### Пакетный inference

```bash
python scripts/train_yolo.py --inference-only --num-test-images 10
```

### Экспорт модели

```python
from ultralytics import YOLO

model = YOLO('models/yolo/yolov8n/weights/best.pt')
model.export(format='onnx')  # или 'torchscript', 'openvino', 'tensorrt'
```
