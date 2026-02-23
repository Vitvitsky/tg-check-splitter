# Task: Implement EditItemsPage

## Parent Domain
006-frontend-pages

## Description
Страница редактирования позиций чека: inline-edit, удаление, добавление.

### UI:
- Список позиций с inline-editing:
  - Tap на название → input для редактирования
  - Tap на цену → input (numeric)
  - Свайп влево → кнопка "Удалить" (или кнопка X)
- Кнопка "+" внизу списка → добавить пустую позицию
- Итого: сумма всех позиций (обновляется при каждом изменении)
- MainButton: "Начать голосование" → сохранить изменения + генерировать QR/invite link

### При "Начать голосование":
1. PUT /api/sessions/{id}/items с обновлёнными данными
2. Обновить статус на "voting"
3. Показать QR-код и invite link (на отдельном экране или модалка)
4. Навигация на VotingPage

### QR + Invite:
- Ссылка: `https://t.me/botname?startapp={invite_code}`
- QR-код: использовать JS библиотеку (qrcode.react или подобную)
- Кнопка "Поделиться" → Telegram share

## Files to Create/Modify
- webapp/src/pages/EditItemsPage.tsx (modify) — полная реализация
- webapp/src/components/EditableItem.tsx (create) — inline-editable item row
- webapp/src/components/QRInvite.tsx (create) — QR code + invite link + share button

## Dependencies
- 005-03-api-client (useUpdateItems, useFinishVoting)
- 005-02-telegram-sdk (MainButton)
- 005-05-routing

## Tests Required
- `npm run build`
- Manual testing

## Acceptance Criteria
- [ ] Inline editing названий и цен
- [ ] Удаление позиций (свайп или кнопка)
- [ ] Добавление позиций
- [ ] Итого пересчитывается в реальном времени
- [ ] Сохранение через API
- [ ] QR-код и invite link генерируются
- [ ] MainButton интегрирован

## Estimated Complexity
L

## Status: in-progress
## Assigned: worker-37743
