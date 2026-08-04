import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { openInvoice } from "@telegram-apps/sdk-react";
import { useQuota, usePurchaseScans } from "@/api/queries";
import { Header, Card, Button, CtaBar } from "@/components/ui";

const PACKS = [
  { scans: 5, stars: 50, blurb: "Best for casual use" },
  { scans: 20, stars: 150, blurb: "For regular groups" },
] as const;

export default function PaymentQuotaPage() {
  const navigate = useNavigate();
  const { data: quota, isLoading } = useQuota();
  const [selected, setSelected] = useState<number>(PACKS[0].scans);
  const [error, setError] = useState<string | null>(null);
  const purchase = usePurchaseScans();

  const handlePurchase = async () => {
    setError(null);
    try {
      const { invoice_link } = await purchase.mutateAsync(selected);
      await openInvoice(invoice_link, "url");
    } catch {
      setError("Could not start the payment. Please try again.");
    }
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-tg-secondary-bg">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-tg-button border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-tg-secondary-bg">
      <Header title="Scan Limit" onBack={() => navigate("/")} />

      <div className="flex-1 flex flex-col items-center justify-center gap-8 px-6">
        {/* Limit info */}
        <div className="flex flex-col items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-warning/15">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-warning">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0110 0v4" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-tg-text">Free scans used up</h2>
          <p className="text-sm text-tg-hint text-center max-w-xs">
            You've used all {3 - (quota?.free_scans_left ?? 0)} free receipt scans this month.
            Purchase additional scans to continue.
          </p>
        </div>

        {/* Plans */}
        <div className="w-full flex flex-col gap-3">
          {PACKS.map((pack) => {
            const isSelected = selected === pack.scans;
            return (
              <Card
                key={pack.scans}
                role="radio"
                ariaChecked={isSelected}
                ariaLabel={`${pack.scans} scans for ${pack.stars} stars`}
                onClick={() => setSelected(pack.scans)}
                className={`flex items-center justify-between p-4 transition-colors ${
                  isSelected ? "ring-2 ring-tg-button" : ""
                }`}
              >
                <div>
                  <p className="text-base font-semibold text-tg-text">
                    {pack.scans} Scans
                  </p>
                  <p className="text-[13px] text-tg-hint">{pack.blurb}</p>
                </div>
                <span
                  className={`px-3 py-1 rounded-full text-sm font-semibold ${
                    isSelected
                      ? "bg-tg-button text-tg-button-text"
                      : "bg-tg-secondary-bg text-tg-text"
                  }`}
                >
                  ⭐ {pack.stars}
                </span>
              </Card>
            );
          })}
        </div>

        {error && (
          <p className="text-center text-sm text-tg-destructive">{error}</p>
        )}
      </div>

      <CtaBar>
        <Button
          variant="main-action"
          className="w-full"
          disabled={purchase.isPending}
          onClick={handlePurchase}
        >
          {purchase.isPending
            ? "Opening…"
            : `Purchase ${selected} scans with ⭐ Stars`}
        </Button>
      </CtaBar>
    </div>
  );
}
