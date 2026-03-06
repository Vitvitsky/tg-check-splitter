import { useCallback, useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSession, useVote } from "@/api/queries";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useTelegramUser, useHaptic } from "@/hooks/useTelegram";
import { Header, Card, Separator, Avatar, Button, CtaBar } from "@/components/ui";
import { currencySymbol } from "@/lib/currency";
import type { Item } from "@/api/types";

export default function VotingPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const user = useTelegramUser();
  const haptic = useHaptic();

  const { data: session, isLoading, isError } = useSession(code ?? "");
  const sessionId = session?.id ?? "";

  useWebSocket(sessionId || null);

  const voteMutation = useVote(sessionId);

  const [optimisticVotes, setOptimisticVotes] = useState<Record<string, number>>({});
  const [pendingItems, setPendingItems] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (session) setOptimisticVotes({});
  }, [session]);

  const currentUserId = user?.id ?? 0;

  const getMyQuantity = useCallback(
    (item: Item): number => {
      if (optimisticVotes[item.id] !== undefined) return optimisticVotes[item.id]!;
      return item.votes.find((v) => v.user_tg_id === currentUserId)?.quantity ?? 0;
    },
    [currentUserId, optimisticVotes],
  );

  const sendVote = useCallback(
    (itemId: string, targetQty: number) => {
      if (!sessionId) return;

      setOptimisticVotes((prev) => ({ ...prev, [itemId]: targetQty }));
      setPendingItems((prev) => new Set(prev).add(itemId));
      haptic.selectionChanged();

      voteMutation.mutate({ itemId, quantity: targetQty }, {
        onSuccess: (result) => {
          setOptimisticVotes((prev) => ({ ...prev, [itemId]: result.quantity }));
          if (result.overflow_prevented) haptic.notificationOccurred("warning");
        },
        onError: () => {
          setOptimisticVotes((prev) => { const next = { ...prev }; delete next[itemId]; return next; });
          haptic.notificationOccurred("error");
        },
        onSettled: () => {
          setPendingItems((prev) => { const next = new Set(prev); next.delete(itemId); return next; });
        },
      });
    },
    [sessionId, haptic, voteMutation],
  );

  const handleClaim = useCallback(
    (itemId: string) => {
      sendVote(itemId, 1);
    },
    [sendVote],
  );

  const handleIncrement = useCallback(
    (itemId: string) => {
      const item = session?.items.find((i) => i.id === itemId);
      if (!item) return;
      const currentQty = getMyQuantity(item);
      const othersTotal = item.votes
        .filter((v) => v.user_tg_id !== currentUserId)
        .reduce((sum, v) => sum + v.quantity, 0);
      const maxForMe = item.quantity - othersTotal;
      if (currentQty >= maxForMe) {
        haptic.notificationOccurred("warning");
        return;
      }
      sendVote(itemId, currentQty + 1);
    },
    [session, currentUserId, getMyQuantity, haptic, sendVote],
  );

  const handleDecrement = useCallback(
    (itemId: string) => {
      const item = session?.items.find((i) => i.id === itemId);
      if (!item) return;
      const currentQty = getMyQuantity(item);
      sendVote(itemId, Math.max(0, currentQty - 1));
    },
    [session, getMyQuantity, sendVote],
  );

  const handleNext = useCallback(() => {
    haptic.impactOccurred("light");
    navigate(`/session/${code}/tip`);
  }, [navigate, code, haptic]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-tg-button border-t-transparent" />
      </div>
    );
  }

  if (isError || !session) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
        <p className="text-tg-destructive">Failed to load session</p>
        <button onClick={() => navigate("/")} className="text-sm text-tg-link underline">Go Home</button>
      </div>
    );
  }

  const isAdmin = session.admin_tg_id === currentUserId;
  const { items, members, currency } = session;
  const totalSelected = items.reduce((sum, item) => sum + getMyQuantity(item), 0);
  const votedCount = members.filter((m) => items.some((it) => it.votes.some((v) => v.user_tg_id === m.user_tg_id && v.quantity > 0))).length;

  return (
    <div className="flex min-h-screen flex-col bg-tg-secondary-bg">
      <Header
        title="Select Your Dishes"
        rightIcon={isAdmin ? "pencil" : undefined}
        onRightAction={isAdmin ? () => navigate(`/session/${code}/admin`) : undefined}
      />

      <div className="flex-1 flex flex-col gap-3 p-4 pb-24">
        {/* Participants row */}
        <div className="flex items-center gap-2 py-1">
          <div className="flex -space-x-1">
            {members.slice(0, 5).map((m) => (
              <Avatar key={m.id} name={m.display_name} size="sm" />
            ))}
          </div>
          <span className="text-[13px] text-tg-hint">{votedCount} / {members.length} voted</span>
        </div>

        {/* Items */}
        <Card>
          {items.map((item, i) => (
            <div key={item.id}>
              {i > 0 && <Separator />}
              <VoteItem
                item={item}
                myQuantity={getMyQuantity(item)}
                isPending={pendingItems.has(item.id)}
                currency={currency}
                onClaim={() => handleClaim(item.id)}
                onIncrement={() => handleIncrement(item.id)}
                onDecrement={() => handleDecrement(item.id)}
              />
            </div>
          ))}
        </Card>
      </div>

      {/* CTA */}
      <CtaBar>
        <Button
          variant="main-action"
          className="w-full"
          disabled={totalSelected === 0}
          onClick={handleNext}
        >
          Confirm Selection
        </Button>
      </CtaBar>
    </div>
  );
}

function VoteItem({
  item,
  myQuantity,
  isPending,
  currency,
  onClaim,
  onIncrement,
  onDecrement,
}: {
  item: Item;
  myQuantity: number;
  isPending: boolean;
  currency: string;
  onClaim: () => void;
  onIncrement: () => void;
  onDecrement: () => void;
}) {
  const unitPrice = item.price / item.quantity;
  const totalClaimed = item.votes.reduce((s, v) => s + v.quantity, 0);
  const sym = currencySymbol(currency);

  return (
    <div className="px-4 py-3">
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0 mr-3">
          <p className="text-[15px] font-medium text-tg-text truncate">{item.name}</p>
          <p className="text-[13px] text-tg-hint">
            {unitPrice.toLocaleString("ru-RU")} {sym} · {totalClaimed > 0 ? `claimed ${totalClaimed}/${item.quantity}` : "not claimed"}
          </p>
        </div>

        {myQuantity > 0 ? (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onDecrement}
              disabled={isPending}
              className="w-8 h-8 flex items-center justify-center rounded-full bg-tg-accent/10 text-tg-accent"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M5 12h14" /></svg>
            </button>
            <span className="w-6 text-center text-[15px] font-semibold text-tg-text">{myQuantity}</span>
            <button
              type="button"
              onClick={onIncrement}
              disabled={isPending}
              className="w-8 h-8 flex items-center justify-center rounded-full bg-tg-accent/10 text-tg-accent"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><path d="M12 5v14M5 12h14" /></svg>
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={onClaim}
            disabled={isPending}
            className="px-4 py-1.5 rounded-[var(--radius-s)] border border-tg-accent/30 text-sm font-medium text-tg-accent active:bg-tg-accent/5"
          >
            Claim
          </button>
        )}
      </div>
    </div>
  );
}
