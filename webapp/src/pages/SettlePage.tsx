import { useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSession, useShares, useSettle } from "@/api/queries";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useTelegramUser, useHaptic } from "@/hooks/useTelegram";
import { Header, Card, SectionLabel, Separator, Badge, Button, CtaBar } from "@/components/ui";
import MemberCardUI from "@/components/ui/MemberCard";
import { formatMoney } from "@/lib/currency";
import type { Share } from "@/api/types";

export default function SettlePage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const user = useTelegramUser();
  const haptic = useHaptic();

  const { data: session, isLoading, isError } = useSession(code ?? "");
  const sessionId = session?.id ?? "";

  useWebSocket(sessionId || null);

  const { data: shares } = useShares(sessionId);
  const settleMutation = useSettle(sessionId);
  const [settledShares, setSettledShares] = useState<Share[] | null>(null);

  const currentUserId = user?.id ?? 0;
  const isAdmin = session?.admin_tg_id === currentUserId;

  const unvotedItems = session?.items.filter((item) => {
    const totalClaimed = item.votes.reduce((s, v) => s + v.quantity, 0);
    return totalClaimed < item.quantity;
  }) ?? [];

  const handleSettle = useCallback(async () => {
    if (!sessionId) return;
    if (unvotedItems.length > 0) {
      navigate(`/session/${code}/unvoted`);
      return;
    }
    haptic.impactOccurred("heavy");
    try {
      const result = await settleMutation.mutateAsync();
      setSettledShares(result);
      haptic.notificationOccurred("success");
    } catch { haptic.notificationOccurred("error"); }
  }, [sessionId, unvotedItems.length, code, navigate, settleMutation, haptic]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-tg-secondary-bg">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-tg-button border-t-transparent" />
      </div>
    );
  }

  if (isError || !session) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center bg-tg-secondary-bg">
        <p className="text-tg-destructive">Failed to load session</p>
        <button onClick={() => navigate("/")} className="text-sm text-tg-link underline">Go Home</button>
      </div>
    );
  }

  const members = session.members;
  const displayShares = settledShares ?? shares ?? [];
  const totalAmount = displayShares.reduce((sum, s) => sum + s.grand_total, 0);
  const isSettled = session.status === "settled" || settledShares !== null;
  const confirmedCount = members.filter((m) => m.confirmed).length;

  return (
    <div className="flex min-h-screen flex-col bg-tg-secondary-bg">
      <Header title="Settlement" />

      <div className="flex-1 flex flex-col gap-4 p-4 pb-24">
        {/* Status banner */}
        {isSettled ? (
          <div className="flex items-center justify-center gap-2 rounded-[var(--radius-m)] bg-success/10 p-3">
            <svg className="w-5 h-5 text-success" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm font-medium text-success">
              All {members.length} participants confirmed!
            </span>
          </div>
        ) : (
          <div className="flex items-center justify-center gap-2 rounded-[var(--radius-m)] bg-tg-button/10 p-3">
            <span className="text-sm text-tg-accent">
              {confirmedCount} / {members.length} confirmed
            </span>
          </div>
        )}

        {/* Participants */}
        <SectionLabel>Participants</SectionLabel>
        <Card>
          {displayShares.length > 0 ? (
            displayShares.map((share, i) => {
              const member = members.find((m) => m.user_tg_id === share.user_tg_id);
              const name = member?.display_name ?? "Unknown";
              const isMe = share.user_tg_id === currentUserId;
              const memberObj = members.find((m) => m.user_tg_id === share.user_tg_id);
              const tipPct = memberObj?.tip_percent ?? 0;
              const subtitle = `${tipPct}% tip`;
              return (
                <div key={share.user_tg_id}>
                  {i > 0 && <Separator />}
                  <MemberCardUI
                    name={isMe ? `${name} (you)` : name}
                    subtitle={subtitle}
                    amount={Math.round(share.grand_total)}
                    currency={session.currency}
                    highlighted={isMe}
                  />
                </div>
              );
            })
          ) : (
            members.map((m, i) => {
              const isMe = m.user_tg_id === currentUserId;
              return (
                <div key={m.id}>
                  {i > 0 && <Separator />}
                  <MemberCardUI
                    name={isMe ? `${m.display_name} (you)` : m.display_name}
                    subtitle={m.confirmed ? "Confirmed" : "Pending"}
                    right={
                      <Badge variant={m.confirmed ? "success" : "warning"}>
                        {m.confirmed ? "Voted" : "Pending"}
                      </Badge>
                    }
                    highlighted={isMe}
                  />
                </div>
              );
            })
          )}
        </Card>

        {/* Total */}
        {displayShares.length > 0 && (
          <Card className="flex items-center justify-between p-4">
            <span className="text-base font-semibold text-tg-text">Check Total</span>
            <span className="text-lg font-bold text-tg-accent">
              {formatMoney(totalAmount, session.currency)}
            </span>
          </Card>
        )}
      </div>

      {/* CTA */}
      {isAdmin && !isSettled && (
        <CtaBar>
          <Button
            variant="main-action"
            className="w-full"
            disabled={settleMutation.isPending}
            onClick={handleSettle}
          >
            {settleMutation.isPending ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Settling...
              </span>
            ) : (
              "Settle & Notify All"
            )}
          </Button>
        </CtaBar>
      )}
    </div>
  );
}
