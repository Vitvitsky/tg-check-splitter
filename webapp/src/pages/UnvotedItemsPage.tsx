import { useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSession } from "@/api/queries";
import { Header, Card, SectionLabel, Button, CtaBar } from "@/components/ui";

export default function UnvotedItemsPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { data: session, isLoading } = useSession(code ?? "");

  const [decisions, setDecisions] = useState<Record<string, "split" | "remove">>({});

  const unclaimedItems = session?.items.filter((item) => {
    const totalClaimed = item.votes.reduce((s, v) => s + v.quantity, 0);
    return totalClaimed === 0;
  }) ?? [];

  const handleDecision = useCallback((itemId: string, decision: "split" | "remove") => {
    setDecisions((prev) => ({ ...prev, [itemId]: decision }));
  }, []);

  const handleContinue = useCallback(() => {
    // TODO: send decisions to API
    navigate(`/session/${code}/settle`);
  }, [navigate, code]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-tg-secondary-bg">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-tg-button border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-tg-secondary-bg">
      <Header title="Unclaimed Items" />

      <div className="flex-1 flex flex-col gap-4 p-4 pb-24">
        {/* Info banner */}
        <div className="flex items-start gap-2.5 rounded-[var(--radius-m)] bg-warning/10 p-3">
          <svg className="w-5 h-5 text-warning shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          <p className="text-sm text-tg-text">
            {unclaimedItems.length} items were not claimed by anyone. Choose what to do with each.
          </p>
        </div>

        <SectionLabel>Unclaimed Items</SectionLabel>

        <div className="flex flex-col gap-4">
          {unclaimedItems.map((item) => (
            <Card key={item.id} className="p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-[15px] font-medium text-tg-text">{item.name}</span>
                <span className="text-[15px] font-semibold text-tg-text">
                  {(item.price * item.quantity).toLocaleString("ru-RU")} ₽
                </span>
              </div>
              <div className="flex gap-3">
                <Button
                  variant={decisions[item.id] === "split" ? "primary" : "secondary"}
                  className="flex-1 py-2 text-sm"
                  onClick={() => handleDecision(item.id, "split")}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5" />
                  </svg>
                  Split equally
                </Button>
                <Button
                  variant={decisions[item.id] === "remove" ? "destructive" : "secondary"}
                  className="flex-1 py-2 text-sm"
                  onClick={() => handleDecision(item.id, "remove")}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                  </svg>
                  Remove
                </Button>
              </div>
            </Card>
          ))}
        </div>

        {/* Reopen voting */}
        <button
          type="button"
          onClick={() => navigate(`/session/${code}/vote`)}
          className="flex items-center gap-2 text-sm font-medium text-tg-accent py-2"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M1 4v6h6M23 20v-6h-6" />
            <path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15" />
          </svg>
          Reopen Voting
        </button>
      </div>

      <CtaBar>
        <Button variant="main-action" className="w-full" onClick={handleContinue}>
          Continue to Settlement
        </Button>
      </CtaBar>
    </div>
  );
}
