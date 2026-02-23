# Task: Implement HomePage

## Parent Domain
006-frontend-pages

## Description
Реализовать главную страницу Mini App: список сессий пользователя + кнопка создания нового чека + квота.

### UI:
- Заголовок: "Мои чеки" (или локализовано)
- Кнопка "Новый чек" (prominent, сверху) → навигация на `/scan`
- Список активных сессий (`useMySessions()` hook):
  - Каждая сессия: invite_code, статус, дата, кол-во участников, кол-во позиций
  - Tap → навигация на `/session/:code/vote` (если voting) или `/session/:code/settle` (если settled)
- Квота (`useQuota()` hook):
  - "Бесплатных сканов: X/3" или "Оплаченных: Y"
  - Если квота исчерпана — предупреждение + кнопка "Купить в боте"
- Empty state: "У вас пока нет чеков. Сфотографируйте чек!"

### Telegram Integration:
- MainButton: не используется на HomePage
- Theme: bg-color из Telegram theme

## Files to Create/Modify
- webapp/src/pages/HomePage.tsx (modify) — полная реализация
- webapp/src/components/SessionCard.tsx (create) — карточка сессии для списка

## Dependencies
- 005-03-api-client (useMySessions, useQuota hooks)
- 005-05-routing

## Tests Required
- Визуальная проверка
- `npm run build` проходит

## Acceptance Criteria
- [ ] Список сессий отображается
- [ ] Кнопка "Новый чек" → `/scan`
- [ ] Квота отображается
- [ ] Empty state для нулевых сессий
- [ ] Tap на сессию → навигация
- [ ] Telegram theme применяется

## Estimated Complexity
M

## Status: in-progress
## Assigned: worker-37709
