# Domain: REST API Routes

## Priority
HIGH

## Scope
- Все REST endpoints, обёртки над существующими сервисами
- `api/routes/sessions.py` — CRUD сессий, join, finish, settle
- `api/routes/voting.py` — vote, tip, confirm, shares
- `api/routes/ocr.py` — photo upload, OCR trigger, item CRUD
- `api/routes/quota.py` — quota info
- `api/routes/__init__.py` — router aggregation
- Тесты для каждого route-модуля

## Dependencies
- 001-api-foundation (app, auth, deps)
- 002-api-schemas (request/response models)

## Key Decisions
- Каждый route использует `Depends(get_current_user)` для auth и `Depends(get_db)` для DB
- Services инстанцируются в каждом endpoint: `svc = SessionService(db)`
- Photo upload через `UploadFile` (multipart), ограничение 5MB
- OCR: принимает session_id, читает фото из БД, скачивает через httpx, вызывает OcrService
- Settle endpoint: вызывает `calculate_shares()` и возвращает результат
- Авторизация: проверка что пользователь — member сессии (для voting), admin (для finish/settle/edit)
- HTTP status codes: 404 (session not found), 403 (not member/admin), 409 (already joined), 400 (bad state)

## Acceptance Criteria
- Все endpoints из плана миграции реализованы
- Auth проверка на каждом endpoint
- Проверка прав (admin vs member) где необходимо
- Корректные HTTP коды ошибок
- Тесты: happy path + error cases для каждого endpoint
- Тесты используют TestClient с мок-initData

## Estimated Tasks
- sessions routes (create, get by invite, get by id, join, finish, settle)
- voting routes (vote, tip, confirm, shares)
- ocr routes (upload photos, trigger OCR, item CRUD)
- quota routes
- router aggregation + mount on app
- integration tests for sessions
- integration tests for voting
- integration tests for ocr
- integration tests for quota
