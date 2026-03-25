\# Инженерный ИскИн



Система машинного обучения для автоматизации эксплуатации 

зданий и сооружений.



\## Функции

\- Журнал ремонтных работ

\- Автоматическое распознавание показаний счётчиков (OCR)

\- Детекция повреждений конструкций (YOLOv8)

\- Генерация отчётов и актов



\## Стек

Python 3.12 · FastAPI · Streamlit · YOLOv8 · EasyOCR · SQLite



\## Установка

```bash

git clone https://github.com/ваш\_ник/IngeneerAI

cd IngeneerAI

python -m venv venv

venv\\Scripts\\activate

pip install -r requirements.txt

```



\## Запуск

```bash

uvicorn src.main:app --reload

streamlit run src/ui/app.py

```

