# Task: Implement Telegram initData auth

## Parent Domain
001-api-foundation

## Description
Реализовать валидацию Telegram Mini App initData через HMAC-SHA256.

### Алгоритм валидации:
1. Парсинг initData из заголовка `Authorization: tma <initData>`
2. Parse initData как URL-encoded string
3. Извлечь `hash` параметр, остальные отсортировать по ключу
4. Сформировать `data_check_string` = отсортированные пары `key=value` через `\n`
5. `secret_key = HMAC_SHA256("WebAppData", bot_token)`
6. `computed_hash = HMAC_SHA256(secret_key, data_check_string)`
7. Сравнить `computed_hash` с `hash` (hex)
8. Проверить `auth_date` — не старше 24 часов

### TelegramUser dataclass:
```python
@dataclass
class TelegramUser:
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    photo_url: str | None = None
```

### FastAPI Dependency:
```python
async def get_current_user(authorization: str = Header(...)) -> TelegramUser:
    # Валидирует initData, возвращает TelegramUser
    # Raises HTTPException(401) при невалидной подписи или expired
```

## Files to Create/Modify
- api/auth.py (create) — TelegramUser, validate_init_data(), get_current_user dependency

## Dependencies
- 001-01-api-package-structure

## Tests Required
- `tests/test_api/test_auth.py`:
  - test_valid_init_data — генерируем валидный initData с правильным HMAC
  - test_invalid_hash — неправильная подпись → 401
  - test_expired_init_data — auth_date > 24h → 401
  - test_missing_header — нет Authorization → 422
  - test_wrong_prefix — не "tma" → 401
  - test_parse_user — корректный парсинг user JSON из initData

## Acceptance Criteria
- [ ] TelegramUser dataclass определён
- [ ] validate_init_data() корректно валидирует HMAC
- [ ] get_current_user() FastAPI dependency работает
- [ ] 401 при невалидной подписи
- [ ] 401 при expired auth_date (>24h)
- [ ] Все тесты проходят

## Estimated Complexity
M

## Status: done
## Assigned: worker-92930
