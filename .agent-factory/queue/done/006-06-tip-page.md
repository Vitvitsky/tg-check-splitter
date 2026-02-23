# Task: Implement TipPage (tips + personal summary + confirm)

## Parent Domain
006-frontend-pages

## Description
Страница выбора чаевых, личная сводка и подтверждение.

### UI:
- TipSlider: 0%–25%
  - Preset buttons: 0%, 5%, 10%, 15%, 20%, 25%
  - Slider для точного значения
  - Haptic feedback при смене preset
- Личная сводка:
  - Список выбранных блюд с ценами и количеством
  - Подитог (dishes_total)
  - Чаевые X% = Y₽ (tip_amount)
  - **Итого: Z₽** (grand_total) — крупным шрифтом
- MainButton: "Подтвердить" → `useConfirm()` + navigate to SettlePage (если admin) или "Ожидание"

### После подтверждения:
- Если обычный участник: показать "Ваш выбор подтверждён! Ожидайте итогов"
- Если admin: показать прогресс подтверждений + навигация на SettlePage

### Пересчёт:
- При смене tip_percent → `useSetTip()` → пересчитать сводку через `useMyShare()`

## Files to Create/Modify
- webapp/src/pages/TipPage.tsx (modify) — полная реализация
- webapp/src/components/TipSlider.tsx (create) — slider + presets
- webapp/src/components/ShareBreakdown.tsx (create) — детализация доли

## Dependencies
- 005-03-api-client (useSetTip, useConfirm, useMyShare)
- 005-02-telegram-sdk (MainButton, haptics)
- 005-05-routing

## Tests Required
- `npm run build`

## Acceptance Criteria
- [ ] TipSlider работает (presets + custom)
- [ ] Сводка пересчитывается при смене tip
- [ ] Подтверждение работает
- [ ] Разные flow для admin и обычного участника
- [ ] Haptic feedback
- [ ] MainButton интегрирован

## Estimated Complexity
M

## Status: in-progress
## Assigned: worker-37794
