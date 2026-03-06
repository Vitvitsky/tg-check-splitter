import { useNavigate } from "react-router-dom";
import { useMySessions, useCreateSession, useClearHistory } from "@/api/queries";
import { Header, Card, SectionLabel, Separator } from "@/components/ui";
import SessionCard from "@/components/SessionCard";

const STATUS_ROUTE: Record<string, string> = {
  created: "edit",
  voting: "vote",
  closed: "settle",
  settled: "history",
};

export default function HomePage() {
  const navigate = useNavigate();
  const { data: sessions, isLoading } = useMySessions();
  const createSession = useCreateSession();
  const clearHistory = useClearHistory();

  const handleNewCheck = async () => {
    try {
      const session = await createSession.mutateAsync("RUB");
      navigate(`/scan`, { state: { sessionId: session.id, inviteCode: session.invite_code } });
    } catch {
      // handled by react-query
    }
  };

  const handleSessionClick = (inviteCode: string, status: string) => {
    const route = STATUS_ROUTE[status] ?? "edit";
    navigate(`/session/${inviteCode}/${route}`);
  };

  const active = sessions?.filter((s) => s.status !== "settled")
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()) ?? [];
  const history = sessions?.filter((s) => s.status === "settled")
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()) ?? [];

  return (
    <div className="flex min-h-screen flex-col bg-tg-secondary-bg">
      <Header title="Check Splitter" showBack={false} />

      <div className="flex-1 flex flex-col gap-4 p-4">
        {isLoading ? (
          <LoadingSkeleton />
        ) : sessions && sessions.length > 0 ? (
          <>
            {active.length > 0 && (
              <>
                <SectionLabel>Active Sessions</SectionLabel>
                <Card>
                  {active.map((s, i) => (
                    <div key={s.id}>
                      {i > 0 && <Separator />}
                      <SessionCard
                        session={s}
                        onClick={() => handleSessionClick(s.invite_code, s.status)}
                      />
                    </div>
                  ))}
                </Card>
              </>
            )}

            {history.length > 0 && (
              <>
                <div className="flex items-center justify-between">
                  <SectionLabel>History</SectionLabel>
                  <button
                    type="button"
                    onClick={() => clearHistory.mutate()}
                    disabled={clearHistory.isPending}
                    className="text-xs text-tg-destructive font-medium px-2 py-1 active:opacity-70"
                  >
                    {clearHistory.isPending ? "Clearing..." : "Clear All"}
                  </button>
                </div>
                <Card>
                  {history.map((s, i) => (
                    <div key={s.id}>
                      {i > 0 && <Separator />}
                      <SessionCard
                        session={s}
                        onClick={() => handleSessionClick(s.invite_code, s.status)}
                      />
                    </div>
                  ))}
                </Card>
              </>
            )}
          </>
        ) : (
          <EmptyState />
        )}
      </div>

      {/* FAB */}
      <button
        type="button"
        onClick={handleNewCheck}
        disabled={createSession.isPending}
        className="fixed right-5 bottom-24 z-30 flex h-14 w-14 items-center justify-center rounded-full bg-tg-button text-white shadow-lg active:opacity-80 disabled:opacity-50"
      >
        {createSession.isPending ? (
          <span className="h-6 w-6 animate-spin rounded-full border-2 border-white border-t-transparent" />
        ) : (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14.5 4h-5L7 7H4a2 2 0 00-2 2v9a2 2 0 002 2h16a2 2 0 002-2V9a2 2 0 00-2-2h-3l-2.5-3z" />
            <circle cx="12" cy="13" r="3" />
          </svg>
        )}
      </button>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex animate-pulse items-center gap-3 rounded-[var(--radius-l)] bg-tg-section-bg p-4">
          <div className="h-5 w-5 rounded-full bg-tg-secondary-bg" />
          <div className="flex-1 flex flex-col gap-2">
            <div className="h-4 w-28 rounded bg-tg-secondary-bg" />
            <div className="h-3 w-40 rounded bg-tg-secondary-bg" />
          </div>
          <div className="h-4 w-16 rounded bg-tg-secondary-bg" />
        </div>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 py-16">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-tg-section-bg">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-tg-hint">
          <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" />
          <rect x="9" y="3" width="6" height="4" rx="1" />
          <path d="M9 14h6M9 18h6" />
        </svg>
      </div>
      <span className="text-sm text-tg-hint">No checks yet</span>
      <span className="text-xs text-tg-hint">Take a photo of a receipt to get started</span>
    </div>
  );
}
