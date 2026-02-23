# Task: API client with auth and TanStack Query hooks

## Parent Domain
005-frontend-skeleton

## Description
Создать API client и TanStack Query hooks для взаимодействия с backend.

### Файлы:

1. **src/api/client.ts** — fetch wrapper:
```typescript
export async function fetchApi<T>(url: string, options?: RequestInit): Promise<T> {
  const initData = getInitData() // from Telegram SDK
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `tma ${initData}`,
      ...options?.headers,
    },
  })
  if (!res.ok) {
    if (res.status === 401) {
      // initData expired — show "reopen app" message
    }
    throw new ApiError(res.status, await res.json())
  }
  return res.json()
}
```

2. **src/api/queries.ts** — TanStack Query hooks:
```typescript
// Queries
export function useSession(inviteCode: string)
export function useSessionById(sessionId: string)
export function useMySessions()
export function useShares(sessionId: string)
export function useMyShare(sessionId: string)
export function useQuota()

// Mutations
export function useCreateSession()
export function useJoinSession()
export function useVote(sessionId: string)
export function useSetTip(sessionId: string)
export function useConfirm(sessionId: string)
export function useUnconfirm(sessionId: string)
export function useUploadPhotos(sessionId: string)
export function useTriggerOcr(sessionId: string)
export function useUpdateItems(sessionId: string)
export function useDeleteItem(sessionId: string)
export function useFinishVoting(sessionId: string)
export function useSettle(sessionId: string)
```

3. **src/api/types.ts** — TypeScript types matching backend schemas:
```typescript
export interface Session { ... }
export interface SessionBrief { ... }
export interface Item { ... }
export interface Member { ... }
export interface Vote { ... }
export interface Share { ... }
export interface OcrResult { ... }
export interface Quota { ... }
```

4. **src/main.tsx** — QueryClientProvider setup

## Files to Create/Modify
- webapp/src/api/client.ts (create)
- webapp/src/api/queries.ts (create)
- webapp/src/api/types.ts (create)
- webapp/src/main.tsx (modify) — add QueryClientProvider

## Dependencies
- 005-01-frontend-init
- 005-02-telegram-sdk (для initData)

## Tests Required
- TypeScript compilation: `npx tsc --noEmit`
- Unit tests для fetchApi error handling (optional)

## Acceptance Criteria
- [ ] fetchApi автоматически добавляет auth header
- [ ] Все query hooks определены и типизированы
- [ ] Mutation hooks используют optimistic updates где возможно
- [ ] QueryClientProvider настроен в main.tsx
- [ ] TypeScript types соответствуют backend schemas
- [ ] Компиляция без ошибок

## Estimated Complexity
L

## Status: done
## Assigned: worker-24552
