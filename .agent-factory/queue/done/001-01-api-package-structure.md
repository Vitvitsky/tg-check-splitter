# Task: Create API package structure

## Parent Domain
001-api-foundation

## Description
Создать базовую структуру пакета `api/` с пустыми модулями и entrypoint.

Структура:
```
api/
├── __init__.py
├── __main__.py          # uvicorn entrypoint
├── app.py               # FastAPI app factory (пустой create_app)
├── auth.py              # placeholder
├── deps.py              # placeholder
└── routes/
    ├── __init__.py
    ├── sessions.py      # placeholder
    ├── voting.py        # placeholder
    ├── ocr.py           # placeholder
    └── quota.py         # placeholder
```

`__main__.py` должен запускать uvicorn:
```python
import uvicorn
from api.app import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("api.app:create_app", factory=True, host="0.0.0.0", port=8000, reload=True)
```

Также обновить `pyproject.toml`: добавить зависимости fastapi, uvicorn[standard], python-multipart.

## Files to Create/Modify
- api/__init__.py (create)
- api/__main__.py (create)
- api/app.py (create) — минимальный create_app()
- api/auth.py (create) — placeholder
- api/deps.py (create) — placeholder
- api/routes/__init__.py (create)
- api/routes/sessions.py (create) — placeholder
- api/routes/voting.py (create) — placeholder
- api/routes/ocr.py (create) — placeholder
- api/routes/quota.py (create) — placeholder
- pyproject.toml (modify) — добавить fastapi, uvicorn, python-multipart

## Dependencies
- None

## Tests Required
- Нет (структура + placeholders)

## Acceptance Criteria
- [ ] `api/` пакет создан со всеми файлами
- [ ] `python -m api` запускается без ошибок (uvicorn стартует)
- [ ] pyproject.toml содержит новые зависимости
- [ ] `uv run python -c "from api.app import create_app; app = create_app(); print(type(app))"` работает

## Estimated Complexity
S

## Status: done
## Assigned: worker-91119
