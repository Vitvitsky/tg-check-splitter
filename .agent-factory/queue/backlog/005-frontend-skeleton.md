# Domain: Frontend Skeleton

## Priority
MEDIUM

## Scope
- Инициализация React + Vite + TypeScript проекта (`webapp/`)
- Telegram SDK интеграция (`@telegram-apps/sdk-react`)
- Tailwind CSS 4 настройка с Telegram theme variables
- TanStack Query setup
- API client с initData auth (`src/api/client.ts`)
- WebSocket client hook (`src/api/ws.ts`, `src/hooks/useWebSocket.ts`)
- TanStack Query hooks (`src/api/queries.ts`)
- React Router routing (`src/App.tsx`)
- Telegram helpers: theme sync, back button, haptics (`src/hooks/useTelegram.ts`)
- Vite proxy для dev (`/api` → `localhost:8000`)

## Dependencies
- 001-api-foundation (нужен работающий API для proxy)

## Key Decisions
- Никаких тяжёлых UI-библиотек — кастомные компоненты под Telegram design language
- `fetchWithAuth(url, options)` — добавляет `Authorization: tma <initData>` к каждому запросу
- WebSocket hook: auto-reconnect с exponential backoff, при event → invalidate TanStack Query cache
- Telegram theme: маппинг CSS vars (`--tg-theme-*`) на Tailwind custom properties
- Routing: `/`, `/scan`, `/session/:code`, `/session/:code/edit`, `/session/:code/vote`, `/session/:code/tip`, `/session/:code/settle`
- MainButton и BackButton через Telegram SDK

## Acceptance Criteria
- `npm run dev` запускает dev-сервер с hot reload
- Telegram SDK инициализируется корректно
- API client отправляет auth header
- WebSocket hook подключается и получает events
- TanStack Query hooks определены для всех основных запросов
- Routing работает между всеми страницами
- Tailwind + Telegram theme variables применяются

## Estimated Tasks
- Init Vite + React + TypeScript project
- Tailwind CSS 4 + Telegram theme setup
- Telegram SDK provider + helpers
- API client with auth
- TanStack Query setup + hooks
- WebSocket client hook
- React Router routing
- Vite config (proxy, aliases)
