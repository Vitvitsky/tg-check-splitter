# Task: React Router routing setup

## Parent Domain
005-frontend-skeleton

## Description
Настроить React Router с lazy-loaded pages.

### src/App.tsx:
```typescript
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { lazy, Suspense } from 'react'

const HomePage = lazy(() => import('@/pages/HomePage'))
const ScanPage = lazy(() => import('@/pages/ScanPage'))
const EditItemsPage = lazy(() => import('@/pages/EditItemsPage'))
const JoinPage = lazy(() => import('@/pages/JoinPage'))
const VotingPage = lazy(() => import('@/pages/VotingPage'))
const TipPage = lazy(() => import('@/pages/TipPage'))
const SettlePage = lazy(() => import('@/pages/SettlePage'))

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingSpinner />}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/scan" element={<ScanPage />} />
          <Route path="/session/:code" element={<JoinPage />} />
          <Route path="/session/:code/edit" element={<EditItemsPage />} />
          <Route path="/session/:code/vote" element={<VotingPage />} />
          <Route path="/session/:code/tip" element={<TipPage />} />
          <Route path="/session/:code/settle" element={<SettlePage />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
```

Создать placeholder-страницы для каждого route (просто div с названием).

### Layout:
Опциональный общий Layout с BackButton handler:
```typescript
function Layout({ children }) {
  const navigate = useNavigate()
  const backButton = useBackButton()
  // Show back button on non-home routes
  // On click → navigate(-1)
}
```

## Files to Create/Modify
- webapp/src/App.tsx (modify) — routing setup
- webapp/src/pages/HomePage.tsx (create) — placeholder
- webapp/src/pages/ScanPage.tsx (create) — placeholder
- webapp/src/pages/EditItemsPage.tsx (create) — placeholder
- webapp/src/pages/JoinPage.tsx (create) — placeholder
- webapp/src/pages/VotingPage.tsx (create) — placeholder
- webapp/src/pages/TipPage.tsx (create) — placeholder
- webapp/src/pages/SettlePage.tsx (create) — placeholder
- webapp/src/components/LoadingSpinner.tsx (create)

## Dependencies
- 005-01-frontend-init
- 005-02-telegram-sdk (BackButton)

## Tests Required
- `npm run build` проходит
- Навигация между страницами работает в dev mode

## Acceptance Criteria
- [ ] Все routes определены
- [ ] Lazy loading работает (code splitting)
- [ ] Placeholder страницы рендерятся
- [ ] BackButton интегрирован
- [ ] Build проходит без ошибок

## Estimated Complexity
M

## Status: done
## Assigned: worker-24586
