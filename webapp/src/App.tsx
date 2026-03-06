import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense } from "react";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 5000 },
  },
});

const HomePage = lazy(() => import("@/pages/HomePage"));
const ScanPage = lazy(() => import("@/pages/ScanPage"));
const EditItemsPage = lazy(() => import("@/pages/EditItemsPage"));
const JoinPage = lazy(() => import("@/pages/JoinPage"));
const VotingPage = lazy(() => import("@/pages/VotingPage"));
const TipPage = lazy(() => import("@/pages/TipPage"));
const SettlePage = lazy(() => import("@/pages/SettlePage"));
const VotingAdminPage = lazy(() => import("@/pages/VotingAdminPage"));
const UnvotedItemsPage = lazy(() => import("@/pages/UnvotedItemsPage"));
const PaymentQuotaPage = lazy(() => import("@/pages/PaymentQuotaPage"));
const SessionHistoryPage = lazy(() => import("@/pages/SessionHistoryPage"));
const ShareSessionPage = lazy(() => import("@/pages/ShareSessionPage"));

function Loading() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-tg-secondary-bg">
      <div className="animate-spin h-8 w-8 border-2 border-tg-button border-t-transparent rounded-full" />
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Suspense fallback={<Loading />}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/scan" element={<ScanPage />} />
            <Route path="/quota" element={<PaymentQuotaPage />} />
            <Route path="/session/:code" element={<JoinPage />} />
            <Route path="/session/:code/edit" element={<EditItemsPage />} />
            <Route path="/session/:code/vote" element={<VotingPage />} />
            <Route path="/session/:code/tip" element={<TipPage />} />
            <Route path="/session/:code/settle" element={<SettlePage />} />
            <Route path="/session/:code/admin" element={<VotingAdminPage />} />
            <Route path="/session/:code/unvoted" element={<UnvotedItemsPage />} />
            <Route path="/session/:code/share" element={<ShareSessionPage />} />
            <Route path="/session/:code/history" element={<SessionHistoryPage />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
