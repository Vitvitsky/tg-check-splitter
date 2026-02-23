# Domain: Bot ↔ Mini App Integration

## Priority
LOW

## Scope
- Обновление `/start` handler: без deep link → WebAppInfo кнопка, с deep link → redirect в Mini App
- Обновление QR/invite генерации: ссылка `https://t.me/botname/appname?startapp={invite_code}`
- Push-уведомления через бота (при завершении сессии, новом участнике)
- Telegram Stars: Mini App показывает "Оплатите в боте", бот обрабатывает оплату
- Настройка `Settings.webapp_url` для Mini App URL

## Dependencies
- 001-api-foundation (settings с webapp_url)
- 003-api-routes (API должен работать)
- 005-frontend-skeleton (Mini App должен быть deploy-ready)

## Key Decisions
- Бот и Mini App работают параллельно (fallback на inline-кнопки остаётся)
- Stars оплата остаётся в боте — Mini App перенаправляет в чат бота
- Push notifications: бот вызывает Telegram API напрямую (sendMessage) при событиях
- WebAppInfo URL из settings.webapp_url

## Acceptance Criteria
- `/start` без аргументов: кнопка "Открыть Mini App"
- `/start {invite_code}`: открывает Mini App с кодом
- QR-код содержит Mini App deep link
- Уведомления отправляются при завершении сессии
- Существующий функционал бота не сломан
- Тесты обновлены

## Estimated Tasks
- Update /start handler for Mini App
- Update invite link generation
- Add push notification service
- Update settings for webapp_url
- Tests
