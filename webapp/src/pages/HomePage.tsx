import { useNavigate } from "react-router-dom";
import { useMySessions, useQuota, useCreateSession } from "@/api/queries";
import SessionCard from "@/components/SessionCard";

const STATUS_ROUTE: Record<string, string> = {
  created: "edit",
  voting: "vote",
  closed: "settle",
  settled: "settle",
};

export default function HomePage() {
  const navigate = useNavigate();
  const { data: sessions, isLoading: sessionsLoading } = useMySessions();
  const { data: quota, isLoading: quotaLoading } = useQuota();
  const createSession = useCreateSession();

  const handleNewCheck = async () => {
    try {
      const session = await createSession.mutateAsync("RUB");
      navigate(`/scan`, { state: { sessionId: session.id, inviteCode: session.invite_code } });
    } catch {
      // mutation error handled by react-query
    }
  };

  const handleSessionClick = (inviteCode: string, status: string) => {
    const route = STATUS_ROUTE[status] ?? "edit";
    navigate(`/session/${inviteCode}/${route}`);
  };

  const isLoading = sessionsLoading || quotaLoading;

  return (
    <div className="flex min-h-screen flex-col bg-[var(--color-tg-bg)]">
      {/* Header */}
      <div className="flex items-center justify-between p-4 pb-2">
        <h1 className="text-xl font-semibold text-[var(--color-tg-text)]">
          Мои чеки
        </h1>
        {quota && !quotaLoading && (
          <QuotaBadge
            freeLeft={quota.free_scans_left}
            paid={quota.paid_scans}
          />
        )}
      </div>

      {/* CTA Button */}
      <div className="px-4 pb-3 pt-1">
        <button
          type="button"
          onClick={handleNewCheck}
          disabled={createSession.isPending}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--color-tg-button)] px-4 py-3.5 text-base font-semibold text-[var(--color-tg-button-text)] shadow-sm transition-opacity active:opacity-80 disabled:opacity-60"
        >
          {createSession.isPending ? (
            <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-tg-button-text)] border-t-transparent" />
          ) : (
            <span className="text-lg">+</span>
          )}
          Новый чек
        </button>
      </div>

      {/* Quota info */}
      {quota && !quotaLoading && (
        <div className="mx-4 mb-3 flex items-center gap-3 rounded-xl bg-[var(--color-tg-section-bg)] px-4 py-3">
          <div className="flex flex-1 flex-col gap-0.5">
            <span className="text-xs text-[var(--color-tg-hint)]">
              Бесплатных сканов: {quota.free_scans_left}/3
            </span>
            {quota.paid_scans > 0 && (
              <span className="text-xs text-[var(--color-tg-hint)]">
                Оплаченных: {quota.paid_scans}
              </span>
            )}
          </div>
          <QuotaBar used={3 - quota.free_scans_left} total={3} />
        </div>
      )}

      {/* Sessions list */}
      <div className="flex flex-1 flex-col gap-2 px-4 pb-6">
        {isLoading ? (
          <LoadingSkeleton />
        ) : sessions && sessions.length > 0 ? (
          sessions
            .slice()
            .sort(
              (a, b) =>
                new Date(b.created_at).getTime() -
                new Date(a.created_at).getTime(),
            )
            .map((s) => (
              <SessionCard
                key={s.id}
                session={s}
                onClick={() => handleSessionClick(s.invite_code, s.status)}
              />
            ))
        ) : (
          <EmptyState />
        )}
      </div>
    </div>
  );
}

/* ----------- Sub-components ----------- */

function QuotaBadge({
  freeLeft,
  paid,
}: {
  freeLeft: number;
  paid: number;
}) {
  const total = freeLeft + paid;
  return (
    <span
      className={`rounded-full px-2.5 py-1 text-xs font-medium ${
        total > 0
          ? "bg-[var(--color-tg-button)]/10 text-[var(--color-tg-button)]"
          : "bg-[var(--color-tg-destructive)]/10 text-[var(--color-tg-destructive)]"
      }`}
    >
      {total > 0 ? `${total} скан.` : "Нет сканов"}
    </span>
  );
}

function QuotaBar({ used, total }: { used: number; total: number }) {
  const pct = Math.min(100, Math.round((used / total) * 100));
  return (
    <div className="h-1.5 w-16 overflow-hidden rounded-full bg-[var(--color-tg-secondary-bg)]">
      <div
        className="h-full rounded-full bg-[var(--color-tg-button)] transition-all"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="flex animate-pulse items-center gap-3 rounded-xl bg-[var(--color-tg-section-bg)] p-4"
        >
          <div className="h-2.5 w-2.5 rounded-full bg-[var(--color-tg-secondary-bg)]" />
          <div className="flex flex-1 flex-col gap-2">
            <div className="h-3.5 w-24 rounded bg-[var(--color-tg-secondary-bg)]" />
            <div className="h-3 w-40 rounded bg-[var(--color-tg-secondary-bg)]" />
          </div>
          <div className="h-3 w-12 rounded bg-[var(--color-tg-secondary-bg)]" />
        </div>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 py-16">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-tg-secondary-bg)]">
        <span className="text-3xl opacity-40">
          <svg
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-[var(--color-tg-hint)]"
          >
            <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
            <rect x="9" y="3" width="6" height="4" rx="1" />
            <path d="M9 14h6" />
            <path d="M9 18h6" />
          </svg>
        </span>
      </div>
      <span className="text-sm text-[var(--color-tg-hint)]">
        У вас пока нет чеков
      </span>
      <span className="text-xs text-[var(--color-tg-hint)]">
        Сфотографируйте чек, чтобы начать
      </span>
    </div>
  );
}
