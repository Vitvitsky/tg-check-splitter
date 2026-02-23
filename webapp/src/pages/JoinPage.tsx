import { useEffect, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useSession, useJoinSession } from "@/api/queries";
import { ApiError } from "@/api/client";
import { useTelegramUser } from "@/hooks/useTelegram";

export default function JoinPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const user = useTelegramUser();
  const {
    data: session,
    isLoading,
    error,
  } = useSession(code ?? "");
  const joinMutation = useJoinSession();

  // Check if current user is already a member
  const isAlreadyMember = useMemo(() => {
    if (!session || !user) return false;
    return session.members.some((m) => m.user_tg_id === user.id);
  }, [session, user]);

  // Auto-redirect if already a member
  useEffect(() => {
    if (isAlreadyMember && code) {
      const route =
        session?.status === "created" || session?.status === "voting"
          ? "vote"
          : "settle";
      navigate(`/session/${code}/${route}`, { replace: true });
    }
  }, [isAlreadyMember, code, session?.status, navigate]);

  const handleJoin = async () => {
    if (!code) return;
    try {
      await joinMutation.mutateAsync(code);
      navigate(`/session/${code}/vote`, { replace: true });
    } catch {
      // error handled via joinMutation.error
    }
  };

  // Determine error state
  const apiError = error instanceof ApiError ? error : null;
  const isNotFound = apiError?.status === 404;
  const isSettled =
    session?.status === "settled" || session?.status === "closed";

  // Calculate total
  const totalAmount = useMemo(() => {
    if (!session) return 0;
    return session.items.reduce(
      (sum, item) => sum + item.price * item.quantity,
      0,
    );
  }, [session]);

  // Find admin name
  const adminName = useMemo(() => {
    if (!session) return "";
    const admin = session.members.find(
      (m) => m.user_tg_id === session.admin_tg_id,
    );
    return admin?.display_name ?? "Организатор";
  }, [session]);

  if (isLoading) {
    return <LoadingState />;
  }

  if (isNotFound || (!isLoading && !session)) {
    return <ErrorState title="Чек не найден" subtitle="Возможно, ссылка устарела или была удалена." />;
  }

  if (error && !isNotFound) {
    return <ErrorState title="Ошибка загрузки" subtitle="Не удалось загрузить данные чека. Попробуйте ещё раз." />;
  }

  if (isSettled && !isAlreadyMember) {
    return (
      <ErrorState
        title="Голосование завершено"
        subtitle="Этот чек уже рассчитан. Присоединиться больше нельзя."
      />
    );
  }

  // If already member, we'll redirect via useEffect. Show nothing to avoid flicker.
  if (isAlreadyMember) {
    return <LoadingState />;
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[var(--color-tg-bg)] px-4">
      <div className="w-full max-w-sm">
        {/* Session info card */}
        <div className="rounded-xl bg-[var(--color-tg-section-bg)] p-5 shadow-sm">
          <h1 className="mb-4 text-center text-xl font-semibold text-[var(--color-tg-text)]">
            Присоединиться к чеку
          </h1>

          <div className="flex flex-col gap-3">
            <InfoRow label="Организатор" value={adminName} />
            <InfoRow
              label="Позиций"
              value={String(session?.items.length ?? 0)}
            />
            <InfoRow
              label="Участников"
              value={String(session?.members.length ?? 0)}
            />
            {totalAmount > 0 && (
              <InfoRow
                label="Сумма"
                value={`${totalAmount.toLocaleString("ru-RU")} ${session?.currency ?? "RUB"}`}
              />
            )}
          </div>
        </div>

        {/* Join button */}
        <button
          type="button"
          onClick={handleJoin}
          disabled={joinMutation.isPending}
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--color-tg-button)] px-4 py-3.5 text-base font-semibold text-[var(--color-tg-button-text)] shadow-sm transition-opacity active:opacity-80 disabled:opacity-60"
        >
          {joinMutation.isPending ? (
            <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-[var(--color-tg-button-text)] border-t-transparent" />
          ) : null}
          Присоединиться
        </button>

        {/* Join error */}
        {joinMutation.error && (
          <p className="mt-3 text-center text-sm text-[var(--color-tg-destructive)]">
            Не удалось присоединиться. Попробуйте ещё раз.
          </p>
        )}
      </div>
    </div>
  );
}

/* ----------- Sub-components ----------- */

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-[var(--color-tg-hint)]">{label}</span>
      <span className="text-sm font-medium text-[var(--color-tg-text)]">
        {value}
      </span>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--color-tg-bg)]">
      <div className="animate-spin h-8 w-8 border-2 border-[var(--color-tg-button)] border-t-transparent rounded-full" />
    </div>
  );
}

function ErrorState({
  title,
  subtitle,
}: {
  title: string;
  subtitle: string;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[var(--color-tg-bg)] px-4">
      <div className="w-full max-w-sm rounded-xl bg-[var(--color-tg-section-bg)] p-6 text-center shadow-sm">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-[var(--color-tg-destructive)]/10">
          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-[var(--color-tg-destructive)]"
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M15 9l-6 6" />
            <path d="M9 9l6 6" />
          </svg>
        </div>
        <h2 className="mb-1 text-lg font-semibold text-[var(--color-tg-text)]">
          {title}
        </h2>
        <p className="text-sm text-[var(--color-tg-hint)]">{subtitle}</p>
      </div>
    </div>
  );
}
