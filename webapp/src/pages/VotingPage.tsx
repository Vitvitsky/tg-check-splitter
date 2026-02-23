import { useCallback, useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSession, useVote, useMyShare } from "@/api/queries";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useTelegramUser, useHaptic } from "@/hooks/useTelegram";
import type { Item } from "@/api/types";
import ItemCard from "@/components/ItemCard";

export default function VotingPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const user = useTelegramUser();
  const haptic = useHaptic();

  const { data: session, isLoading, isError } = useSession(code ?? "");
  const sessionId = session?.id ?? "";

  useWebSocket(sessionId || null);

  const voteMutation = useVote(sessionId);
  const { data: myShare } = useMyShare(sessionId);

  // Optimistic local quantity overrides
  const [optimisticVotes, setOptimisticVotes] = useState<
    Record<string, number>
  >({});
  const [pendingItems, setPendingItems] = useState<Set<string>>(new Set());

  // Clear optimistic overrides when server data updates
  useEffect(() => {
    if (session) {
      setOptimisticVotes({});
    }
  }, [session]);

  const currentUserId = user?.id ?? 0;

  const getMyQuantity = useCallback(
    (item: Item): number => {
      if (optimisticVotes[item.id] !== undefined) {
        return optimisticVotes[item.id]!;
      }
      return (
        item.votes.find((v) => v.user_tg_id === currentUserId)?.quantity ?? 0
      );
    },
    [currentUserId, optimisticVotes],
  );

  const handleVote = useCallback(
    (itemId: string) => {
      if (!sessionId) return;

      const item = session?.items.find((i) => i.id === itemId);
      if (!item) return;

      // Calculate optimistic next quantity
      const currentQty = getMyQuantity(item);
      // Total claimed by others
      const othersTotal = item.votes
        .filter((v) => v.user_tg_id !== currentUserId)
        .reduce((sum, v) => sum + v.quantity, 0);
      const maxForMe = item.quantity - othersTotal;
      const nextQty = currentQty >= maxForMe ? 0 : currentQty + 1;

      // Set optimistic state
      setOptimisticVotes((prev) => ({ ...prev, [itemId]: nextQty }));
      setPendingItems((prev) => new Set(prev).add(itemId));

      haptic.selectionChanged();

      voteMutation.mutate(itemId, {
        onSuccess: (result) => {
          // Update optimistic with server truth
          setOptimisticVotes((prev) => ({
            ...prev,
            [itemId]: result.quantity,
          }));
          if (result.overflow_prevented) {
            haptic.notificationOccurred("warning");
          }
        },
        onError: () => {
          // Revert optimistic state
          setOptimisticVotes((prev) => {
            const next = { ...prev };
            delete next[itemId];
            return next;
          });
          haptic.notificationOccurred("error");
        },
        onSettled: () => {
          setPendingItems((prev) => {
            const next = new Set(prev);
            next.delete(itemId);
            return next;
          });
        },
      });
    },
    [sessionId, session, currentUserId, getMyQuantity, haptic, voteMutation],
  );

  const handleNext = useCallback(() => {
    haptic.impactOccurred("light");
    navigate(`/session/${code}/tip`);
  }, [navigate, code, haptic]);

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

  const items = session.items;
  const members = session.members;

  // Count user's total selections
  const totalSelected = items.reduce((sum, item) => sum + getMyQuantity(item), 0);

  return (
    <div className="flex min-h-screen flex-col bg-[var(--color-tg-bg)]">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-[var(--color-tg-bg)] px-4 pb-3 pt-4">
        <h1 className="text-xl font-bold text-[var(--color-tg-text)]">
          Выберите блюда
        </h1>
        <p className="mt-0.5 text-sm text-[var(--color-tg-hint)]">
          Нажмите, чтобы добавить порцию. Повторное нажатие увеличит количество.
        </p>
      </div>

      {/* Items list */}
      <div className="flex-1 space-y-2 px-4 pb-32">
        {items.length === 0 ? (
          <div className="py-12 text-center text-sm text-[var(--color-tg-hint)]">
            Позиции ещё не добавлены
          </div>
        ) : (
          items.map((item) => (
            <ItemCard
              key={item.id}
              item={item}
              members={members}
              currentUserId={currentUserId}
              myQuantity={getMyQuantity(item)}
              onVote={handleVote}
              isVoting={pendingItems.has(item.id)}
            />
          ))
        )}
      </div>

      {/* Sticky bottom bar */}
      <div className="fixed inset-x-0 bottom-0 z-20 border-t border-[var(--color-tg-secondary-bg)] bg-[var(--color-tg-bg)] px-4 pb-[env(safe-area-inset-bottom,8px)] pt-3">
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="text-lg font-bold text-[var(--color-tg-text)]">
              {myShare
                ? `${myShare.dishes_total.toFixed(0)} \u20BD`
                : totalSelected > 0
                  ? "..."
                  : "0 \u20BD"}
            </div>
            <div className="text-xs text-[var(--color-tg-hint)]">
              Ваш итог
            </div>
          </div>
          <button
            onClick={handleNext}
            disabled={totalSelected === 0}
            className={`
              rounded-xl px-6 py-2.5 text-sm font-semibold transition-all duration-150
              active:scale-95
              ${
                totalSelected > 0
                  ? "bg-[var(--color-tg-button)] text-[var(--color-tg-button-text)] shadow-md"
                  : "bg-[var(--color-tg-secondary-bg)] text-[var(--color-tg-hint)] cursor-not-allowed"
              }
            `}
          >
            Далее &rarr; Чаевые
          </button>
        </div>
      </div>
    </div>
  );
}
