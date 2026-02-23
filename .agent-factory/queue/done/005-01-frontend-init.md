# Task: Initialize frontend project (Vite + React + TypeScript + Tailwind)

## Parent Domain
005-frontend-skeleton

## Description
Создать React + TypeScript проект в директории `webapp/` с помощью Vite.

### Шаги:
1. `npm create vite@latest webapp -- --template react-ts`
2. Установить зависимости:
   - `@telegram-apps/sdk-react` — Telegram Mini App SDK
   - `@tanstack/react-query` — серверный стейт
   - `react-router-dom` — роутинг
   - `tailwindcss @tailwindcss/vite` — Tailwind CSS 4
3. Настроить Vite config:
   - Proxy: `/api` → `http://localhost:8000`, `/ws` → ws proxy
   - Resolve aliases: `@` → `src/`
4. Настроить Tailwind CSS 4:
   - Import в main CSS: `@import "tailwindcss";`
   - Telegram theme variables через `@theme`
5. Настроить tsconfig paths

### vite.config.ts:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
})
```

## Files to Create/Modify
- webapp/ (create entire project structure)
- webapp/package.json
- webapp/vite.config.ts
- webapp/tsconfig.json
- webapp/src/main.tsx (minimal entry)
- webapp/src/App.tsx (minimal)
- webapp/src/index.css (Tailwind import + TG theme vars)
- webapp/index.html

## Dependencies
- None (standalone frontend project)

## Tests Required
- `npm run build` проходит без ошибок
- `npm run dev` стартует dev server

## Acceptance Criteria
- [ ] `cd webapp && npm install` устанавливает зависимости
- [ ] `npm run dev` запускает dev-сервер
- [ ] `npm run build` собирает production bundle
- [ ] Tailwind CSS работает (применяются utility classes)
- [ ] Proxy на /api работает в dev mode
- [ ] TypeScript компилируется без ошибок

## Estimated Complexity
M

## Status: done
## Assigned: worker-18997
