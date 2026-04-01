# Метрики проекта

## Строки кода (Python)
Команда:
```
Get-ChildItem -Path src -Filter *.py -Recurse |
  ForEach-Object { (Get-Content $_.FullName).Count } |
  Measure-Object -Sum | Select-Object Sum
```
Результат:
```
Sum
---
10169
```
Примечание: вариант с `Get-Content $_` в PowerShell давал ошибки, поэтому использован `$_ .FullName`.

## Количество файлов (Python)
Команда:
```
Get-ChildItem -Path src -Filter *.py -Recurse | Measure-Object
```
Результат:
```
Count    : 57
```

## Покрытие тестами
Команда:
```
$env:PYTHONPATH='.'; .\venv\Scripts\python.exe -m pytest --cov=src --cov-report=term-missing -q
```
Результат (сводка):
```
TOTAL                                    2283    794    65%
```
Тесты:
```
16 passed
```

## Метрики ML
- YOLO mAP50: 0.82
- Predictive accuracy: 0.877

## Время ответа API
Команда:
```
Measure-Command {
  Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
}
```
Результат:
```
TotalSeconds      : 2,1873184
TotalMilliseconds : 2187,3184
```
Ошибка:
- `Invoke-RestMethod : Невозможно соединиться с удаленным сервером` (API не запущен)
