# Task: Implement OCR and item management routes

## Parent Domain
003-api-routes

## Description
Реализовать endpoints для загрузки фото, OCR и CRUD позиций в `api/routes/ocr.py`.

### Endpoints:

1. **POST /api/sessions/{session_id}/photos** — загрузить фото чека
   - Auth: required, admin check
   - Body: multipart file(s) (UploadFile), limit 5MB each
   - Вызывает: сохранение файла и `SessionService.add_photo()`
   - Note: В текущей реализации фото хранятся по tg_file_id. Для Mini App нужно:
     - Принять файл через multipart
     - Сохранить bytes (или в файловую систему, или в memory для OCR)
     - tg_file_id = сгенерировать UUID placeholder (фото пришло не из Telegram)
   - Returns: `list[PhotoOut]` (201)

2. **POST /api/sessions/{session_id}/ocr** — запустить распознавание
   - Auth: required, admin check
   - Логика:
     - Получить фото сессии
     - Для фото из бота: скачать через Telegram Bot API (httpx)
     - Для фото из Mini App: использовать сохранённые bytes
     - Вызвать `OcrService.parse_receipt(photos_bytes)`
     - Вызвать `SessionService.save_ocr_items()` с результатами
     - Вызвать `SessionService.update_currency()` если определена
   - Returns: `OcrResultOut`

3. **PUT /api/sessions/{session_id}/items** — заменить все позиции
   - Auth: required, admin check
   - Body: `ItemsUpdateIn`
   - Логика: clear_items() + save_ocr_items() с новыми данными
   - Returns: `list[ItemOut]`

4. **PUT /api/sessions/{session_id}/items/{item_id}** — обновить одну позицию
   - Auth: required, admin check
   - Body: `ItemUpdateIn`
   - Вызывает: `SessionService.update_item(item_id, name, price)`
   - Returns: `ItemOut`

5. **DELETE /api/sessions/{session_id}/items/{item_id}** — удалить позицию
   - Auth: required, admin check
   - Вызывает: `SessionService.delete_item(item_id)`
   - Returns: 204

### Хранение фото (Mini App):
Для MVP: фото хранятся в памяти как bytes, привязанные к session_id (dict в app.state).
При OCR: bytes передаются напрямую в OcrService.
Позже можно вынести в S3/file storage.

## Files to Create/Modify
- api/routes/ocr.py (create)
- api/app.py (modify) — include ocr router

## Dependencies
- 001-02-auth-middleware
- 001-03-db-dependency
- 001-04-app-factory
- 002-01-response-schemas
- 002-02-request-schemas

## Tests Required
- `tests/test_api/test_ocr.py`:
  - test_upload_photo (multipart)
  - test_upload_photo_too_large → 413
  - test_upload_photo_not_admin → 403
  - test_ocr_trigger (mock OcrService)
  - test_update_items
  - test_update_single_item
  - test_delete_item
  - test_delete_item_not_admin → 403

## Acceptance Criteria
- [ ] Все 5 endpoints реализованы
- [ ] Admin check на каждом endpoint
- [ ] Photo upload с лимитом 5MB
- [ ] OCR вызывается корректно
- [ ] Item CRUD работает
- [ ] Тесты проходят (OcrService замокан)

## Estimated Complexity
L

## Status: done
## Assigned: worker-7962
