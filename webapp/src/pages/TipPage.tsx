import { useState, useCallback, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSession, useSetTip, useConfirm, useMyShare } from "@/api/queries";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useTelegramUser, useHaptic } from "@/hooks/useTelegram";
import { Header, Card, SectionLabel, Separator, Chip, ReceiptItem, Button, CtaBar } from "@/components/ui";
import CustomTipSheet from "@/components/sheets/CustomTipSheet";
import { formatMoney } from "@/lib/currency";

const TIP_PRESETS = [0, 10, 15, 20];

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
  const currentMember = session?.members.find((m) => m.user_tg_id === currentUserId);

  const [tipPercent, setTipPercent] = useState(10);
  const [isConfirmed, setIsConfirmed] = useState(false);
  const [tipSaved, setTipSaved] = useState(false);
  const [showCustomTip, setShowCustomTip] = useState(false);

  useEffect(() => {
    if (currentMember?.tip_percent != null) setTipPercent(currentMember.tip_percent);
  }, [currentMember?.tip_percent]);

  useEffect(() => {
    if (currentMember?.confirmed) setIsConfirmed(true);
  }, [currentMember?.confirmed]);

  useEffect(() => {
    if (!sessionId || !tipSaved) return;
    const timer = setTimeout(() => setTipMutation.mutate(tipPercent), 300);
    return () => clearTimeout(timer);
  }, [tipPercent, sessionId, tipSaved, setTipMutation]);

  const handleTipChange = useCallback((value: number) => {
    setTipPercent(value);
    setTipSaved(true);
    haptic.selectionChanged();
  }, [haptic]);

  const handleConfirm = useCallback(async () => {
    if (!sessionId) return;
    haptic.impactOccurred("medium");
    try {
      await setTipMutation.mutateAsync(tipPercent);
      await confirmMutation.mutateAsync();
      setIsConfirmed(true);
      haptic.notificationOccurred("success");
    } catch {
      haptic.notificationOccurred("error");
    }
  }, [sessionId, tipPercent, setTipMutation, confirmMutation, haptic]);

  const isAdmin = session?.admin_tg_id === currentUserId;
  const currency = session?.currency ?? "RUB";

  const myItems = session?.items.filter((item) =>
    item.votes.some((v) => v.user_tg_id === currentUserId && v.quantity > 0),
  ) ?? [];

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

  const confirmedCount = session?.members.filter((m) => m.confirmed).length ?? 0;
  const totalMembers = session?.members.length ?? 0;

  if (isConfirmed) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-8 p-6 bg-tg-secondary-bg">
        {/* Success area */}
        <div className="flex flex-col items-center gap-4">
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-success/15">
            <svg className="h-10 w-10 text-success" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
          </div>
          <h2 className="text-[22px] font-bold text-tg-text">Selection confirmed!</h2>
          <p className="text-[15px] text-tg-hint">Your vote has been submitted</p>
        </div>

        {/* Summary card */}
        {myShare && (
          <Card className="w-full p-5">
            <div className="flex flex-col gap-3">
              <div className="flex justify-between text-sm">
                <span className="text-tg-hint">Your items</span>
                <span className="font-semibold text-tg-text">{myItems.length} dishes</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-tg-hint">Subtotal</span>
                <span className="font-semibold text-tg-text">{formatMoney(myShare.dishes_total, currency)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-tg-hint">Tip ({tipPercent}%)</span>
                <span className="font-semibold text-tg-text">{formatMoney(myShare.tip_amount, currency)}</span>
              </div>
              <Separator />
              <div className="flex justify-between">
                <span className="text-base font-bold text-tg-text">Total</span>
                <span className="text-base font-bold text-tg-accent">{formatMoney(myShare.grand_total, currency)}</span>
              </div>
            </div>
          </Card>
        )}

        {/* Waiting area */}
        <div className="flex flex-col items-center gap-2">
          <svg className="w-5 h-5 text-tg-hint" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm text-tg-hint">Waiting for others to confirm...</p>
          <p className="text-[13px] font-medium text-tg-hint">{confirmedCount} of {totalMembers} confirmed</p>
        </div>

        {isAdmin && (
          <Button variant="primary" onClick={() => navigate(`/session/${code}/settle`)} className="w-full">
            Go to Settlement
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-tg-secondary-bg">
      <Header title="Your Share" />

      <div className="flex-1 flex flex-col gap-4 p-4 pb-24">
        {/* Your Items */}
        <SectionLabel>Your Items</SectionLabel>
        <Card>
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
          {myItems.length === 0 && (
            <p className="px-4 py-3 text-sm text-tg-hint">No items selected</p>
          )}
        </Card>

        {/* Tip */}
        <SectionLabel>Tip</SectionLabel>
        <div className="flex items-center gap-2 flex-wrap">
          {TIP_PRESETS.map((p) => (
            <Chip key={p} label={`${p}%`} active={tipPercent === p && !showCustomTip} onClick={() => handleTipChange(p)} />
          ))}
          <Chip
            label="Other"
            active={!TIP_PRESETS.includes(tipPercent)}
            onClick={() => setShowCustomTip(true)}
          />
        </div>

        {/* Summary */}
        <SectionLabel>Summary</SectionLabel>
        <Card className="p-4">
          <div className="flex flex-col gap-3">
            <div className="flex justify-between text-sm">
              <span className="text-tg-hint">Subtotal</span>
              <span className="text-tg-text">{myShare ? formatMoney(myShare.dishes_total, currency) : "..."}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-tg-hint">Tip ({tipPercent}%)</span>
              <span className="text-tg-text">{myShare ? formatMoney(myShare.tip_amount, currency) : "..."}</span>
            </div>
            <Separator />
            <div className="flex justify-between">
              <span className="text-base font-semibold text-tg-text">Total</span>
              <span className="text-lg font-bold text-tg-accent">
                {myShare ? formatMoney(myShare.grand_total, currency) : "..."}
              </span>
            </div>
          </div>
        </Card>
      </div>

      {/* CTA */}
      <CtaBar>
        <Button
          variant="main-action"
          className="w-full"
          disabled={confirmMutation.isPending || setTipMutation.isPending || myItems.length === 0}
          onClick={handleConfirm}
        >
          {confirmMutation.isPending || setTipMutation.isPending ? (
            <span className="flex items-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Saving...
            </span>
          ) : (
            "Confirm & Pay"
          )}
        </Button>
      </CtaBar>

      {/* Custom Tip Sheet */}
      <CustomTipSheet
        open={showCustomTip}
        onClose={() => setShowCustomTip(false)}
        subtotal={myShare?.dishes_total ?? 0}
        currency={currency}
        onApply={handleTipChange}
      />
    </div>
  );
}
