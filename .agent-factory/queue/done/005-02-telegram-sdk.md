# Task: Telegram SDK integration and helpers

## Parent Domain
005-frontend-skeleton

## Description
Интегрировать `@telegram-apps/sdk-react` в приложение: provider, theme sync, back button, haptics.

### Файлы:

1. **src/main.tsx** — обернуть App в SDKProvider:
```tsx
import { SDKProvider } from '@telegram-apps/sdk-react'

ReactDOM.createRoot(root).render(
  <SDKProvider acceptCustomStyles>
    <App />
  </SDKProvider>
)
```

2. **src/hooks/useTelegram.ts** — хелперы:
```typescript
export function useTelegramUser() {
  // Возвращает parsed user из initData
}

export function useInitData() {
  // Возвращает raw initData string для API auth
}

export function useHaptic() {
  // Возвращает { impact, notification, selection }
}

export function useMainButton() {
  // Управление MainButton (text, onClick, show/hide)
}

export function useBackButton() {
  // Управление BackButton (show/hide, onClick)
}
```

3. **src/lib/theme.ts** — маппинг Telegram theme на CSS variables:
```typescript
// Telegram SDK автоматически инжектит --tg-theme-* CSS variables
// Настроить Tailwind для использования этих переменных
```

## Files to Create/Modify
- webapp/src/main.tsx (modify) — SDKProvider
- webapp/src/hooks/useTelegram.ts (create)
- webapp/src/lib/theme.ts (create)
- webapp/src/index.css (modify) — Telegram theme CSS variables mapping

## Dependencies
- 005-01-frontend-init

## Tests Required
- Визуальная проверка (hooks зависят от Telegram runtime)
- Type checking: `npx tsc --noEmit`

## Acceptance Criteria
- [ ] SDKProvider оборачивает приложение
- [ ] useTelegramUser() возвращает данные пользователя
- [ ] useInitData() возвращает raw initData для auth header
- [ ] useHaptic() предоставляет haptic feedback functions
- [ ] Telegram theme variables доступны через Tailwind

## Estimated Complexity
M

## Status: done
## Assigned: worker-24535
