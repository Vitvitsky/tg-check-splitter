import { useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  useSession,
  useShares,
  useFinishVoting,
  useSettle,
} from "@/api/queries";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useTelegramUser, useHaptic } from "@/hooks/useTelegram";
import type { Share } from "@/api/types";
import ProgressBar from "@/components/ProgressBar";
import ShareCard from "@/components/ShareCard";

export default function SettlePage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const user = useTelegramUser();
  const haptic = useHaptic();

  const { data: session, isLoading, isError } = useSession(code ?? "");
  const sessionId = session?.id ?? "";

  useWebSocket(sessionId || null);

  const { data: shares } = useShares(sessionId);
  const finishMutation = useFinishVoting(sessionId);
  const settleMutation = useSettle(sessionId);

  const [settledShares, setSettledShares] = useState<Share[] | null>(null);

  const currentUserId = user?.id ?? 0;
  const isAdmin = session?.admin_tg_id === currentUserId;

  const handleFinish = useCallback(async () => {
    if (!sessionId) return;
    haptic.impactOccurred("medium");

    try {
      await finishMutation.mutateAsync();
      haptic.notificationOccurred("success");
    } catch {
      haptic.notificationOccurred("error");
    }
  }, [sessionId, finishMutation, haptic]);

  const handleSettle = useCallback(async () => {
    if (!sessionId) return;
    haptic.impactOccurred("heavy");

    try {
      const result = await settleMutation.mutateAsync();
      setSettledShares(result);
      haptic.notificationOccurred("success");
    } catch {
      haptic.notificationOccurred("error");
    }
  }, [sessionId, settleMutation, haptic]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--color-tg-button)] border-t-transparent" />
      </div>
    );
  }

  if (isError || !session) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
        <p className="text-base text-[var(--color-tg-destructive)]">
          Не удалось загрузить сессию
        </p>
        <button
          onClick={() => navigate("/")}
          className="text-sm text-[var(--color-tg-link)] underline"
        >
          На главную
        </button>
      </div>
    );
  }

  const members = session.members;
  const displayShares = settledShares ?? shares ?? [];
  const totalAmount = displayShares.reduce((sum, s) => sum + s.grand_total, 0);
  const isSettled = session.status === "settled" || settledShares !== null;

  // Non-admin waiting view
  if (!isAdmin) {
    return (
      <div className="flex min-h-screen flex-col bg-[var(--color-tg-bg)]">
        <div className="px-4 pb-2 pt-4">
          <h1 className="text-xl font-bold text-[var(--color-tg-text)]">
            Ожидание итогов
          </h1>
          <p className="mt-0.5 text-sm text-[var(--color-tg-hint)]">
            Администратор подводит итоги
          </p>
        </div>

        <div className="space-y-4 px-4 py-2">
          <div className="rounded-xl bg-[var(--color-tg-section-bg)] p-4">
            <ProgressBar members={members} />
          </div>

          {displayShares.length > 0 && (
            <div className="space-y-2">
              <h2 className="text-base font-semibold text-[var(--color-tg-text)]">
                Итоги
              </h2>
              {displayShares.map((share) => (
                <ShareCard
                  key={share.user_tg_id}
                  share={share}
                  isCurrentUser={share.user_tg_id === currentUserId}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Admin view
  return (
    <div className="flex min-h-screen flex-col bg-[var(--color-tg-bg)]">
      {/* Header */}
      <div className="px-4 pb-2 pt-4">
        <h1 className="text-xl font-bold text-[var(--color-tg-text)]">
          {isSettled ? "Итоги" : "Завершение"}
        </h1>
        <p className="mt-0.5 text-sm text-[var(--color-tg-hint)]">
          {isSettled
            ? "Счёт разделён!"
            : "Дождитесь подтверждений и завершите"}
        </p>
      </div>

      <div className="flex-1 space-y-4 px-4 pb-32">
        {/* Progress */}
        <div className="rounded-xl bg-[var(--color-tg-section-bg)] p-4">
          <ProgressBar members={members} />
        </div>

        {/* Shares table */}
        {displayShares.length > 0 && (
          <div className="space-y-2">
            <h2 className="text-base font-semibold text-[var(--color-tg-text)]">
              Суммы к оплате
            </h2>
            {displayShares.map((share) => (
              <ShareCard
                key={share.user_tg_id}
                share={share}
                isCurrentUser={share.user_tg_id === currentUserId}
              />
            ))}

            {/* Grand total */}
            <div className="flex items-center justify-between rounded-xl bg-[var(--color-tg-secondary-bg)] p-3">
              <span className="text-sm font-medium text-[var(--color-tg-hint)]">
                Общий счёт
              </span>
              <span className="text-lg font-bold text-[var(--color-tg-text)]">
                {totalAmount.toFixed(0)} &#8381;
              </span>
            </div>
          </div>
        )}

        {/* Settled confirmation */}
        {isSettled && (
          <div className="rounded-xl bg-green-50 p-4 text-center">
            <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
              <svg
                className="h-6 w-6 text-green-600"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4.5 12.75l6 6 9-13.5"
                />
              </svg>
            </div>
            <p className="text-sm font-medium text-green-700">
              Итоги отправлены всем участникам!
            </p>
          </div>
        )}
      </div>

      {/* Sticky bottom actions */}
      {!isSettled && (
        <div className="fixed inset-x-0 bottom-0 z-20 space-y-2 border-t border-[var(--color-tg-secondary-bg)] bg-[var(--color-tg-bg)] px-4 pb-[env(safe-area-inset-bottom,8px)] pt-3">
          {session.status === "voting" && (
            <button
              onClick={handleFinish}
              disabled={finishMutation.isPending}
              className="w-full rounded-xl bg-[var(--color-tg-secondary-bg)] py-2.5 text-sm font-semibold text-[var(--color-tg-text)] transition-all duration-150 active:scale-[0.98]"
            >
              {finishMutation.isPending ? (
                <span className="inline-flex items-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  Завершение...
                </span>
              ) : (
                "Завершить голосование"
              )}
            </button>
          )}
          <button
            onClick={handleSettle}
            disabled={settleMutation.isPending}
            className="w-full rounded-xl bg-[var(--color-tg-button)] py-3 text-base font-semibold text-[var(--color-tg-button-text)] shadow-md transition-all duration-150 active:scale-[0.98]"
          >
            {settleMutation.isPending ? (
              <span className="inline-flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                Расчёт...
              </span>
            ) : (
              "Завершить и отправить итоги"
            )}
          </button>
        </div>
      )}
    </div>
  );
}
