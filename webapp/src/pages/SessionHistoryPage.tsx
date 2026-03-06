import { useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSession, useShares } from "@/api/queries";
import { useTelegramUser } from "@/hooks/useTelegram";
import { Header, Card, SectionLabel, Separator, ReceiptItem, Button } from "@/components/ui";
import { formatMoney } from "@/lib/currency";

export default function SessionHistoryPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const user = useTelegramUser();
  const { data: session, isLoading } = useSession(code ?? "");
  const sessionId = session?.id ?? "";
  const { data: shares } = useShares(sessionId);

  const currentUserId = user?.id ?? 0;

  const myShare = useMemo(
    () => shares?.find((s) => s.user_tg_id === currentUserId),
    [shares, currentUserId],
  );

  const myMember = session?.members.find((m) => m.user_tg_id === currentUserId);
  const tipPct = myMember?.tip_percent ?? session?.tip_percent ?? 0;

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

  const currency = session.currency;

  return (
    <div className="flex min-h-screen flex-col bg-tg-secondary-bg">
      <Header title={`Session #${code}`} />

      <div className="flex-1 flex flex-col items-center gap-4 p-4">
        {/* Status banner */}
        <div className="flex items-center justify-center gap-2 rounded-[var(--radius-m)] bg-success/10 p-3 w-full">
          <svg className="w-[18px] h-[18px] text-success" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm font-semibold text-success">Session settled</span>
        </div>

        {/* Your share hero */}
        {myShare && (
          <div className="flex flex-col items-center gap-1 py-4">
            <span className="text-sm text-tg-hint">Your share</span>
            <span className="text-4xl font-extrabold text-tg-accent">
              {formatMoney(Math.round(myShare.grand_total), currency)}
            </span>
            <span className="text-[13px] text-tg-hint">
              including {tipPct}% tip ({formatMoney(Math.round(myShare.tip_amount), currency)})
            </span>
          </div>
        )}

        {/* Your Items */}
        {myItems.length > 0 && (
          <>
            <SectionLabel>Your Items</SectionLabel>
            <Card className="w-full">
              {myItems.map((item, i) => {
                const myVote = item.votes.find((v) => v.user_tg_id === currentUserId);
                const qty = myVote?.quantity ?? 0;
                const unitPrice = item.price / item.quantity;
                return (
                  <div key={item.id}>
                    {i > 0 && <Separator />}
                    <ReceiptItem name={item.name} quantity={qty} price={Math.round(unitPrice * qty)} currency={currency} />
                  </div>
                );
              })}
            </Card>
          </>
        )}

        {/* Summary card */}
        {myShare && (
          <>
            <SectionLabel>Summary</SectionLabel>
            <Card className="w-full p-4">
              <div className="flex flex-col gap-3">
                <div className="flex justify-between text-sm">
                  <span className="text-tg-hint">Subtotal</span>
                  <span className="font-medium text-tg-text">{formatMoney(myShare.dishes_total, currency)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-tg-hint">Tip ({tipPct}%)</span>
                  <span className="font-medium text-tg-text">{formatMoney(myShare.tip_amount, currency)}</span>
                </div>
                <Separator />
                <div className="flex justify-between">
                  <span className="text-base font-bold text-tg-text">Total</span>
                  <span className="text-base font-bold text-tg-accent">{formatMoney(myShare.grand_total, currency)}</span>
                </div>
              </div>
            </Card>
          </>
        )}

        {/* Action buttons */}
        <div className="flex gap-3 w-full mt-2">
          <Button variant="secondary" className="flex-1" onClick={() => navigate("/")}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            Home
          </Button>
          <Button variant="primary" className="flex-1" onClick={() => navigate(`/session/${code}/share`)}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" />
              <path d="M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98" />
            </svg>
            Share
          </Button>
        </div>
      </div>
    </div>
  );
}
