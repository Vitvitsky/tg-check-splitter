# Task: Implement VotingPage (core screen)

## Parent Domain
006-frontend-pages

## Description
Ключевой экран Mini App: все позиции чека, quantity voting, real-time обновления, текущий итог.

### UI:
- Scroll-список всех позиций (без пагинации!)
- Каждая позиция — ItemCard:
  - Название, цена, количество (из чека)
  - Кнопка +/- для quantity voting (cycle: 0→1→2→...→max→0)
  - Аватары/бейджи тех, кто уже отметил эту позицию (с количеством)
  - Real-time обновление через WebSocket
  - Optimistic update при tap (UI обновляется мгновенно)
  - Haptic feedback: `impactOccurred('light')` при голосовании
- Sticky footer:
  - "Твой текущий итог: 1250₽" (обновляется в реальном времени)
  - Пересчёт через `useMyShare(sessionId)`
- MainButton: "Далее → Чаевые" → навигация на TipPage
- BackButton: → HomePage

### ItemCard component:
```typescript
interface ItemCardProps {
  item: Item
  myQuantity: number  // текущее кол-во от текущего пользователя
  onVote: () => void  // cycle_vote
  voters: Array<{ userId: number, name: string, quantity: number }>
}
```

### WebSocket integration:
- `useWebSocket(sessionId)` — подключается при mount
- При `vote_updated` event → TanStack Query refetch → UI обновляется

## Files to Create/Modify
- webapp/src/pages/VotingPage.tsx (modify) — полная реализация
- webapp/src/components/ItemCard.tsx (create) — карточка позиции
- webapp/src/components/MemberAvatar.tsx (create) — аватар/бейдж участника

## Dependencies
- 005-03-api-client (useSessionById, useVote, useMyShare)
- 005-04-websocket-hook (useWebSocket)
- 005-02-telegram-sdk (MainButton, BackButton, haptics)
- 005-05-routing

## Tests Required
- `npm run build`
- Manual testing с несколькими пользователями

## Acceptance Criteria
- [ ] Все позиции видны (scroll, без пагинации)
- [ ] Quantity voting работает (tap → cycle)
- [ ] Optimistic updates (мгновенная реакция UI)
- [ ] Real-time обновления от других пользователей
- [ ] Текущий итог пересчитывается
- [ ] Аватары voters отображаются
- [ ] Haptic feedback при голосовании
- [ ] MainButton → TipPage
- [ ] Sticky footer с итогом

## Estimated Complexity
L

## Status: in-progress
## Assigned: worker-37777
