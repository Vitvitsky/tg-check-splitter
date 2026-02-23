# Task: Update bot /start to open Mini App

## Parent Domain
007-bot-integration

## Description
Обновить handler `/start` в боте для открытия Mini App.

### Изменения:

1. **Без deep link** (`/start`):
   - Вместо текущего сообщения → показать кнопку `WebAppInfo`
   - "Открыть Mini App" → URL из `settings.webapp_url`

2. **С deep link** (`/start {invite_code}`):
   - Показать кнопку с `WebAppInfo(url="{webapp_url}?startapp={invite_code}")`
   - Или redirect: кнопка "Присоединиться к чеку" → Mini App с code

3. **Обновить генерацию invite link**:
   - Текущий формат: `https://t.me/{bot_username}?start={invite_code}`
   - Новый формат: `https://t.me/{bot_username}/{app_name}?startapp={invite_code}`
   - Оба формата должны работать (backward compatibility)

4. **Обновить QR-код**:
   - QR содержит Mini App deep link

5. **Добавить webapp_url в Settings** (если не добавлен в 001-04):
   - `webapp_url: str = "http://localhost:5173"`

## Files to Create/Modify
- bot/handlers/start.py (modify) — WebAppInfo кнопка
- bot/handlers/admin.py (modify) — обновить invite link + QR
- bot/config.py (modify) — webapp_url если не добавлен

## Dependencies
- 001-04-app-factory (webapp_url в Settings)

## Tests Required
- Обновить существующие тесты start handler
- test_start_shows_webapp_button
- test_start_with_deep_link
- test_invite_link_format

## Acceptance Criteria
- [ ] /start показывает кнопку Mini App
- [ ] Deep link открывает Mini App с invite_code
- [ ] QR-код содержит Mini App link
- [ ] Существующий функционал бота не сломан
- [ ] Тесты обновлены и проходят

## Estimated Complexity
M

## Status: todo
## Assigned: none
