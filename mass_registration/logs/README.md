# Логи планировщика

Здесь сохраняются JSON логи с результатами каждого запуска.

Формат имени: `scheduler_YYYYMMDD_HHMMSS.json`

Пример содержимого:
```json
{
  "total": 20,
  "success": 18,
  "failed": 2,
  "errors": 0,
  "start_time": "2025-10-19T01:00:00",
  "end_time": "2025-10-19T01:45:00",
  "runs": [
    {
      "run_number": 1,
      "success": true,
      "email": "abc@example.com",
      "duration": 234.5
    }
  ]
}
```
