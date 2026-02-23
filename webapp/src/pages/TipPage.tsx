import { useState, useCallback, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSession, useSetTip, useConfirm, useMyShare } from "@/api/queries";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useTelegramUser, useHaptic } from "@/hooks/useTelegram";
import TipSlider from "@/components/TipSlider";

export default function TipPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const user = useTelegramUser();
  const haptic = useHaptic();

  const { data: session, isLoading, isError } = useSession(code ?? "");
  const sessionId = session?.id ?? "";

  useWebSocket(sessionId || null);

  const setTipMutation = useSetTip(sessionId);
  const confirmMutation = useConfirm(sessionId);
  const { data: myShare } = useMyShare(sessionId);

  const currentUserId = user?.id ?? 0;

  // Find current member to get existing tip
  const currentMember = session?.members.find(
    (m) => m.user_tg_id === currentUserId,
  );

  const [tipPercent, setTipPercent] = useState(10);
  const [isConfirmed, setIsConfirmed] = useState(false);
  const [tipSaved, setTipSaved] = useState(false);

  // Initialize tip from member data
  useEffect(() => {
    if (currentMember?.tip_percent != null) {
      setTipPercent(currentMember.tip_percent);
    }
  }, [currentMember?.tip_percent]);

  // Update confirmed state from server
  useEffect(() => {
    if (currentMember?.confirmed) {
      setIsConfirmed(true);
    }
  }, [currentMember?.confirmed]);

  // Debounced tip save
  useEffect(() => {
    if (!sessionId || !tipSaved) return;

    const timer = setTimeout(() => {
      setTipMutation.mutate(tipPercent);
    }, 300);
    return () => clearTimeout(timer);
  }, [tipPercent, sessionId, tipSaved, setTipMutation]);

  const handleTipChange = useCallback(
    (value: number) => {
      setTipPercent(value);
      setTipSaved(true);
      haptic.selectionChanged();
    },
    [haptic],
  );

  const handleConfirm = useCallback(async () => {
    if (!sessionId) return;

    haptic.impactOccurred("medium");

    try {
      // Save tip first, then confirm
      await setTipMutation.mutateAsync(tipPercent);
      await confirmMutation.mutateAsync();
      setIsConfirmed(true);
      haptic.notificationOccurred("success");
    } catch {
      haptic.notificationOccurred("error");
    }
  }, [sessionId, tipPercent, setTipMutation, confirmMutation, haptic]);

  const isAdmin = session?.admin_tg_id === currentUserId;

  // Items the user voted for
  const myItems =
    session?.items.filter(
      (item) =>
        item.votes.some(
          (v) => v.user_tg_id === currentUserId && v.quantity > 0,
        ),
    ) ?? [];

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

  if (isConfirmed) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
          <svg
            className="h-8 w-8 text-green-600"
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
        <h2 className="text-xl font-bold text-[var(--color-tg-text)]">
          Ваш выбор подтверждён!
        </h2>
        <p className="text-sm text-[var(--color-tg-hint)]">
          Ожидайте итогов от администратора
        </p>
        {myShare && (
          <div className="mt-2 text-2xl font-bold text-[var(--color-tg-button)]">
            {myShare.grand_total.toFixed(0)} &#8381;
          </div>
        )}
        {isAdmin && (
          <button
            onClick={() => navigate(`/session/${code}/settle`)}
            className="mt-4 rounded-xl bg-[var(--color-tg-button)] px-6 py-2.5 text-sm font-semibold text-[var(--color-tg-button-text)] shadow-md transition-all duration-150 active:scale-95"
          >
            Перейти к итогам
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-[var(--color-tg-bg)]">
      {/* Header */}
      <div className="px-4 pb-2 pt-4">
        <h1 className="text-xl font-bold text-[var(--color-tg-text)]">
          Чаевые
        </h1>
        <p className="mt-0.5 text-sm text-[var(--color-tg-hint)]">
          Выберите размер чаевых
        </p>
      </div>

      <div className="flex-1 space-y-4 px-4 pb-32">
        {/* Tip selector */}
        <div className="rounded-xl bg-[var(--color-tg-section-bg)] p-4">
          <TipSlider value={tipPercent} onChange={handleTipChange} />
        </div>

        {/* Personal summary */}
        <div className="rounded-xl bg-[var(--color-tg-section-bg)] p-4">
          <h2 className="mb-3 text-base font-semibold text-[var(--color-tg-text)]">
            Ваш заказ
          </h2>

          {/* Selected items */}
          {myItems.length > 0 ? (
            <div className="space-y-2">
              {myItems.map((item) => {
                const myVote = item.votes.find(
                  (v) => v.user_tg_id === currentUserId,
                );
                const qty = myVote?.quantity ?? 0;
                const unitPrice = item.price / item.quantity;
                return (
                  <div
                    key={item.id}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="text-[var(--color-tg-text)]">
                      {item.name}
                      {qty > 1 && (
                        <span className="ml-1 text-[var(--color-tg-hint)]">
                          &times;{qty}
                        </span>
                      )}
                    </span>
                    <span className="font-medium text-[var(--color-tg-text)]">
                      {(unitPrice * qty).toFixed(0)} &#8381;
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-[var(--color-tg-hint)]">
              Вы ещё не выбрали блюда
            </p>
          )}

          {/* Divider */}
          <div className="my-3 h-px bg-[var(--color-tg-secondary-bg)]" />

          {/* Totals */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-sm">
              <span className="text-[var(--color-tg-hint)]">Подитог</span>
              <span className="text-[var(--color-tg-text)]">
                {myShare ? `${myShare.dishes_total.toFixed(0)} \u20BD` : "..."}
              </span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-[var(--color-tg-hint)]">
                Чаевые ({tipPercent}%)
              </span>
              <span className="text-[var(--color-tg-text)]">
                {myShare ? `${myShare.tip_amount.toFixed(0)} \u20BD` : "..."}
              </span>
            </div>
            <div className="my-1.5 h-px bg-[var(--color-tg-secondary-bg)]" />
            <div className="flex items-center justify-between">
              <span className="text-base font-semibold text-[var(--color-tg-text)]">
                Итого
              </span>
              <span className="text-xl font-bold text-[var(--color-tg-button)]">
                {myShare
                  ? `${myShare.grand_total.toFixed(0)} \u20BD`
                  : "..."}
              </span>
            </div>
          </div>
        </div>

        {/* Back to voting link */}
        <button
          onClick={() => navigate(`/session/${code}/vote`)}
          className="text-sm text-[var(--color-tg-link)] underline"
        >
          &larr; Вернуться к выбору блюд
        </button>
      </div>

      {/* Sticky bottom bar */}
      <div className="fixed inset-x-0 bottom-0 z-20 border-t border-[var(--color-tg-secondary-bg)] bg-[var(--color-tg-bg)] px-4 pb-[env(safe-area-inset-bottom,8px)] pt-3">
        <button
          onClick={handleConfirm}
          disabled={
            confirmMutation.isPending ||
            setTipMutation.isPending ||
            myItems.length === 0
          }
          className={`
            w-full rounded-xl py-3 text-base font-semibold transition-all duration-150
            active:scale-[0.98]
            ${
              myItems.length > 0
                ? "bg-[var(--color-tg-button)] text-[var(--color-tg-button-text)] shadow-md"
                : "bg-[var(--color-tg-secondary-bg)] text-[var(--color-tg-hint)] cursor-not-allowed"
            }
          `}
        >
          {confirmMutation.isPending || setTipMutation.isPending ? (
            <span className="inline-flex items-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
              Сохранение...
            </span>
          ) : (
            "Подтвердить"
          )}
        </button>
      </div>
    </div>
  );
}
