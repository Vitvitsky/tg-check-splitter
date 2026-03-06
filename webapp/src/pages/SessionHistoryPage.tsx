import { useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSession, useShares } from "@/api/queries";
import { useTelegramUser } from "@/hooks/useTelegram";
import { Header, Card, SectionLabel, Separator, ReceiptItem } from "@/components/ui";
import MemberCardUI from "@/components/ui/MemberCard";
import { formatMoney } from "@/lib/currency";

export default function SessionHistoryPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const user = useTelegramUser();
  const { data: session, isLoading } = useSession(code ?? "");
  const sessionId = session?.id ?? "";
  const { data: shares } = useShares(sessionId);

  const currentUserId = user?.id ?? 0;

  const totalAmount = useMemo(
    () => shares?.reduce((sum, s) => sum + s.grand_total, 0) ?? 0,
    [shares],
  );

  const myItems = useMemo(() => {
    if (!session) return [];
    return session.items.filter((item) =>
      item.votes.some((v) => v.user_tg_id === currentUserId && v.quantity > 0),
    );
  }, [session, currentUserId]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-tg-secondary-bg">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-tg-button border-t-transparent" />
      </div>
    );
  }

  if (!session) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 bg-tg-secondary-bg">
        <p className="text-tg-destructive">Session not found</p>
        <button onClick={() => navigate("/")} className="text-sm text-tg-link underline">Go Home</button>
      </div>
    );
  }

  const settledDate = session.closed_at ? new Date(session.closed_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "";

  return (
    <div className="flex min-h-screen flex-col bg-tg-secondary-bg">
      <Header title={`Session #${code}`} />

      <div className="flex-1 flex flex-col gap-4 p-4">
        {/* Status banner */}
        <div className="flex items-center justify-center gap-2 rounded-[var(--radius-m)] bg-success/10 p-3">
          <svg className="w-5 h-5 text-success" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm font-medium text-success">Settled on {settledDate}</span>
        </div>

        {/* Info card */}
        <Card className="flex items-center justify-around p-4 text-center">
          <div>
            <p className="text-lg font-bold text-tg-text">{formatMoney(totalAmount, session.currency)}</p>
            <p className="text-xs text-tg-hint">Total</p>
          </div>
          <div>
            <p className="text-lg font-bold text-tg-text">{session.members.length}</p>
            <p className="text-xs text-tg-hint">People</p>
          </div>
          <div>
            <p className="text-lg font-bold text-tg-text">{session.items.length}</p>
            <p className="text-xs text-tg-hint">Items</p>
          </div>
        </Card>

        {/* Participants */}
        <SectionLabel>Participants</SectionLabel>
        <Card>
          {(shares ?? []).map((share, i) => {
            const member = session.members.find((m) => m.user_tg_id === share.user_tg_id);
            const name = member?.display_name ?? "Unknown";
            const isMe = share.user_tg_id === currentUserId;
            const tipPct = member?.tip_percent ?? 0;
            return (
              <div key={share.user_tg_id}>
                {i > 0 && <Separator />}
                <MemberCardUI
                  name={isMe ? `${name} (you)` : name}
                  subtitle={`${tipPct}% tip`}
                  amount={Math.round(share.grand_total)}
                  currency={session.currency}
                  highlighted={isMe}
                />
              </div>
            );
          })}
        </Card>

        {/* Your Items */}
        {myItems.length > 0 && (
          <>
            <SectionLabel>Your Items</SectionLabel>
            <Card>
              {myItems.map((item, i) => {
                const myVote = item.votes.find((v) => v.user_tg_id === currentUserId);
                const qty = myVote?.quantity ?? 0;
                const unitPrice = item.price / item.quantity;
                return (
                  <div key={item.id}>
                    {i > 0 && <Separator />}
                    <ReceiptItem name={item.name} quantity={qty} price={Math.round(unitPrice * qty)} currency={session.currency} />
                  </div>
                );
              })}
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
