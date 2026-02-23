# Task: WebSocket client hook

## Parent Domain
005-frontend-skeleton

## Description
Создать React hook для WebSocket подключения с auto-reconnect и интеграцией с TanStack Query.

### src/hooks/useWebSocket.ts:
```typescript
export function useWebSocket(sessionId: string | null) {
  // 1. Подключается к ws://host/ws/{sessionId}?token={initData}
  // 2. Auto-reconnect с exponential backoff (1s, 2s, 4s, 8s, max 30s)
  // 3. При получении event:
  //    - Парсит JSON
  //    - Invalidates соответствующие TanStack Query keys:
  //      "vote_updated" → invalidate ["session", sessionId]
  //      "member_joined" → invalidate ["session", sessionId]
  //      "member_confirmed" → invalidate ["session", sessionId]
  //      "tip_changed" → invalidate ["session", sessionId]
  //      "session_status" → invalidate ["session", sessionId]
  //      "items_updated" → invalidate ["session", sessionId]
  // 4. Cleanup при unmount
  // 5. Return: { isConnected, lastEvent }
}
```

### Event types:
```typescript
export type WsEventType =
  | 'vote_updated'
  | 'member_joined'
  | 'member_confirmed'
  | 'member_unconfirmed'
  | 'tip_changed'
  | 'session_status'
  | 'items_updated'

export interface WsEvent {
  type: WsEventType
  data: Record<string, unknown>
}
```

## Files to Create/Modify
- webapp/src/hooks/useWebSocket.ts (create)
- webapp/src/api/ws.ts (create) — low-level WS wrapper с reconnect

## Dependencies
- 005-01-frontend-init
- 005-02-telegram-sdk (для initData)
- 005-03-api-client (для TanStack Query client)

## Tests Required
- TypeScript compilation
- Manual testing with running backend

## Acceptance Criteria
- [ ] Hook подключается к WS при наличии sessionId
- [ ] Auto-reconnect с exponential backoff
- [ ] TanStack Query cache invalidation при events
- [ ] Cleanup при unmount (no memory leaks)
- [ ] isConnected state корректно обновляется
- [ ] TypeScript compilation без ошибок

## Estimated Complexity
M

## Status: done
## Assigned: worker-24569
