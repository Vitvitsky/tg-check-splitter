# Domain: Frontend Pages & Components

## Priority
LOW

## Scope
Все экраны Mini App и переиспользуемые компоненты:

### Pages (7)
- `HomePage` — список сессий + "Новый чек" + квота
- `ScanPage` — загрузка фото + OCR + превью результата
- `EditItemsPage` — inline-edit позиций, свайп-удаление, добавление
- `JoinPage` — присоединение по invite_code (deep link)
- `VotingPage` — ключевой экран: все позиции, quantity voting, real-time, текущий итог
- `TipPage` — слайдер чаевых + личная сводка + подтверждение
- `SettlePage` — прогресс подтверждений, таблица долей, неотмеченные, завершение

### Shared Components
- `ItemCard` — карточка позиции (голосование, аватары)
- `MemberAvatar` — аватар участника
- `TipSlider` — слайдер чаевых (0-25%)
- `ShareCard` — карточка доли (имя → сумма)
- `ProgressBar` — прогресс подтверждений (2/5)
- `QRCode` — QR для invite link

## Dependencies
- 005-frontend-skeleton (routing, API client, hooks, theme)
- 003-api-routes (API endpoints для данных)
- 004-websocket (real-time обновления для VotingPage)

## Key Decisions
- VotingPage — scroll вместо пагинации, все позиции видны
- Quantity cycling: tap на кнопку +/- (0→1→2→...→0), аналогично боту
- TipSlider: preset значения (0, 5, 10, 15, 20, 25), свободный ввод через slider
- Optimistic updates для голосования (UI обновляется мгновенно)
- Haptic feedback: `impactOccurred('light')` при голосовании, `notificationOccurred('success')` при подтверждении
- MainButton от Telegram SDK для основных CTA
- Responsive: адаптация под compact/expanded Mini App
- Photo upload: client-side resize (canvas → blob, max 5MB)

## Acceptance Criteria
- Все 7 страниц функциональны и подключены к API
- Real-time обновления на VotingPage через WebSocket
- Optimistic updates для smooth UX
- Haptic feedback работает
- Telegram theme (light/dark) применяется корректно
- MainButton и BackButton интегрированы
- Responsive дизайн для разных размеров Mini App

## Estimated Tasks
- HomePage
- ScanPage + photo upload component
- EditItemsPage + inline editing
- JoinPage
- VotingPage + ItemCard component
- TipPage + TipSlider component
- SettlePage + ShareCard + ProgressBar
- QRCode component
- MemberAvatar component
