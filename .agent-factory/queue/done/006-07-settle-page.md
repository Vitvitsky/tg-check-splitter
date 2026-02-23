# Task: Implement SettlePage (admin only)

## Parent Domain
006-frontend-pages

## Description
Страница финального расчёта для админа: прогресс подтверждений, доли, неотмеченные позиции, завершение.

### UI:
- Прогресс: "Подтвердили: 3/5" + ProgressBar + аватары (confirmed в зелёном, pending в сером)
- Real-time обновление через WebSocket (member_confirmed events)
- Таблица долей (`useShares(sessionId)`):
  - Каждый участник: аватар, имя, сумма с чаевыми
  - Highlight для текущего пользователя
- Секция "Неотмеченные позиции" (если есть items без votes):
  - Список таких позиций
  - Опции для каждой: "Разделить поровну" / "Убрать из счёта"
  - "Разделить поровну" → `add_vote_all` для всех members
  - "Убрать" → `delete_item`
- MainButton: "Завершить и отправить итоги" → `useSettle()`
  - После settle → показать финальный экран с долями
  - `notificationOccurred('success')` haptic

### Доступ:
- Только admin (если не admin → redirect на VotingPage/TipPage)

## Files to Create/Modify
- webapp/src/pages/SettlePage.tsx (modify) — полная реализация
- webapp/src/components/ProgressBar.tsx (create) — прогресс подтверждений
- webapp/src/components/ShareCard.tsx (create) — карточка доли участника

## Dependencies
- 005-03-api-client (useShares, useSettle, useFinishVoting)
- 005-04-websocket-hook (real-time member_confirmed)
- 005-02-telegram-sdk (MainButton, haptics)
- 005-05-routing

## Tests Required
- `npm run build`

## Acceptance Criteria
- [ ] Прогресс подтверждений отображается и обновляется real-time
- [ ] Таблица долей корректна
- [ ] Неотмеченные позиции обрабатываются
- [ ] Admin-only доступ
- [ ] Settle → финальный результат
- [ ] Haptic feedback

## Estimated Complexity
L

## Status: in-progress
## Assigned: worker-37811
