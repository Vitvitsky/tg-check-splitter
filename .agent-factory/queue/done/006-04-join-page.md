# Task: Implement JoinPage

## Parent Domain
006-frontend-pages

## Description
Страница присоединения к сессии по invite_code (deep link).

### UI:
- При открытии Mini App по deep link `/session/:code`:
  - Загрузить сессию по invite_code (`useSession(code)`)
  - Показать: кол-во позиций, итого, кол-во участников, имя админа
  - Кнопка "Присоединиться" → `useJoinSession()`
  - После join → навигация на `/session/:code/vote`
- Если уже member → сразу redirect на VotingPage
- Если сессия не найдена → "Чек не найден"
- Если сессия уже settled → "Голосование завершено"

### Edge cases:
- Автоматический join + redirect если уже member
- Loading state при загрузке сессии
- Error state при 404

## Files to Create/Modify
- webapp/src/pages/JoinPage.tsx (modify) — полная реализация

## Dependencies
- 005-03-api-client (useSession, useJoinSession)
- 005-02-telegram-sdk (MainButton)
- 005-05-routing

## Tests Required
- `npm run build`

## Acceptance Criteria
- [ ] Информация о сессии отображается
- [ ] "Присоединиться" → join + redirect на VotingPage
- [ ] Redirect если уже member
- [ ] Error states (404, settled)

## Estimated Complexity
S

## Status: in-progress
## Assigned: worker-37760
