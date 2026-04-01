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
TOTAL                                    3226   1694    47%
```
Ошибки:
- `TypeError: AsyncClient.__init__() got an unexpected keyword argument 'app'` (httpx)
- `sqlite3.IntegrityError: UNIQUE constraint failed: meter_types.code` (seed_data)

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
