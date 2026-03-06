import { useNavigate } from "react-router-dom";
import { useQuota } from "@/api/queries";
import { Header, Card, Button, CtaBar } from "@/components/ui";

export default function PaymentQuotaPage() {
  const navigate = useNavigate();
  const { data: quota, isLoading } = useQuota();

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
          <Card className="flex items-center justify-between p-4">
            <div>
              <p className="text-base font-semibold text-tg-text">5 Scans</p>
              <p className="text-[13px] text-tg-hint">Best for casual use</p>
            </div>
            <span className="px-3 py-1 rounded-full bg-tg-button text-tg-button-text text-sm font-semibold">
              ⭐ 50
            </span>
          </Card>

          <Card className="flex items-center justify-between p-4">
            <div>
              <p className="text-base font-semibold text-tg-text">20 Scans</p>
              <p className="text-[13px] text-tg-hint">For regular groups</p>
            </div>
            <span className="px-3 py-1 rounded-full bg-tg-secondary-bg text-tg-text text-sm font-semibold">
              ⭐ 150
            </span>
          </Card>
        </div>
      </div>

      <CtaBar>
        <Button variant="main-action" className="w-full">
          Purchase with ⭐ Stars
        </Button>
      </CtaBar>
    </div>
  );
}
