# Task: Create API test fixtures and conftest

## Parent Domain
003-api-routes

## Description
Создать тестовую инфраструктуру для API тестов: conftest с TestClient, мок-initData, DB fixtures.

### Что нужно:

1. **`tests/test_api/__init__.py`** — пакет тестов

2. **`tests/test_api/conftest.py`**:
   - Фикстура `app` — создаёт FastAPI app с переопределёнными dependencies
   - Фикстура `client` — httpx.AsyncClient с TestClient transport
   - Фикстура `db_session` — переиспользует из основного conftest (SQLite in-memory)
   - Фикстура `auth_headers` — генерирует валидный initData для тестового user
   - Хелпер `make_init_data(user_id, first_name, ...)` — генерирует initData с правильным HMAC

### make_init_data helper:
```python
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

TEST_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"

def make_init_data(user_id: int = 12345, first_name: str = "Test", **kwargs) -> str:
    user = {"id": user_id, "first_name": first_name, **kwargs}
    params = {
        "user": json.dumps(user, separators=(",", ":")),
        "auth_date": str(int(time.time())),
        "query_id": "test_query_id",
    }
    # Sort and create data_check_string
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    # HMAC
    secret_key = hmac.new(b"WebAppData", TEST_BOT_TOKEN.encode(), hashlib.sha256).digest()
    hash_value = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    params["hash"] = hash_value
    return urlencode(params)
```

### Переопределение dependencies:
```python
app.dependency_overrides[get_db] = lambda: db_session
app.dependency_overrides[get_settings] = lambda: test_settings  # с TEST_BOT_TOKEN
```

## Files to Create/Modify
- tests/test_api/__init__.py (create)
- tests/test_api/conftest.py (create)

## Dependencies
- 001-02-auth-middleware (чтобы знать формат auth)
- 001-04-app-factory (чтобы знать create_app)

## Tests Required
- Это сама тестовая инфраструктура. Проверить что fixtures работают:
  - test_client_works — simple GET /api/health → 200

## Acceptance Criteria
- [ ] conftest.py создан с auth helper
- [ ] TestClient работает с async
- [ ] make_init_data() генерирует валидный initData
- [ ] DB fixture переиспользует существующий SQLite pattern
- [ ] Простой тест проходит

## Estimated Complexity
M

## Status: done
## Assigned: worker-3353
