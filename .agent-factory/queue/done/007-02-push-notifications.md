# Task: Push notifications from Mini App events

## Parent Domain
007-bot-integration

## Description
Бот отправляет push-уведомления участникам при ключевых событиях из Mini App.

### Уведомления:

1. **Сессия завершена (settled)**:
   - Каждому участнику: "Чек рассчитан! Ваша доля: X₽"
   - Кнопка "Посмотреть детали" → Mini App

2. **Новый участник (member_joined)**:
   - Админу: "{Name} присоединился к чеку"

### Реализация:

Вариант A (простой): API endpoint вызывает бота напрямую
- `POST /api/internal/notify` (internal, без public auth)
- Бот вызывает `bot.send_message()` через Telegram Bot API

Вариант B (event-driven): REST routes после мутации вызывают notification service
- Notification service использует httpx для вызова Telegram Bot API напрямую (без aiogram)
- Более чистое разделение, не требует запущенного бота

Рекомендуется **Вариант B**: notification service в `api/services/notifications.py` который вызывает Telegram Bot API через httpx.

```python
class NotificationService:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    async def send_message(self, chat_id: int, text: str, reply_markup: dict | None = None):
        async with httpx.AsyncClient() as client:
            await client.post(f"{self.base_url}/sendMessage", json={
                "chat_id": chat_id,
                "text": text,
                "reply_markup": reply_markup,
            })
```

## Files to Create/Modify
- api/services/notifications.py (create) — NotificationService
- api/routes/sessions.py (modify) — вызвать notification при settle

## Dependencies
- 003-01-session-routes (settle endpoint)

## Tests Required
- test_notification_on_settle (mock httpx)
- test_notification_on_join (mock httpx)

## Acceptance Criteria
- [ ] При settle: все участники получают уведомление с долей
- [ ] При join: админ получает уведомление
- [ ] Notification service не блокирует API response
- [ ] Тесты проходят (httpx замокан)

## Estimated Complexity
M

## Status: todo
## Assigned: none
