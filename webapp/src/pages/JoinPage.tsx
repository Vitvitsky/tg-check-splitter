import { useEffect, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useSession, useJoinSession } from "@/api/queries";
import { ApiError } from "@/api/client";
import { useTelegramUser } from "@/hooks/useTelegram";
import { Header, Card, Button, CtaBar } from "@/components/ui";

export default function JoinPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const user = useTelegramUser();
  const { data: session, isLoading, error } = useSession(code ?? "");
  const joinMutation = useJoinSession();

  const isAlreadyMember = useMemo(() => {
    if (!session || !user) return false;
    return session.members.some((m) => m.user_tg_id === user.id);
  }, [session, user]);

  useEffect(() => {
    if (isAlreadyMember && code) {
      const route = session?.status === "created" || session?.status === "voting" ? "vote" : "settle";
      navigate(`/session/${code}/${route}`, { replace: true });
    }
  }, [isAlreadyMember, code, session?.status, navigate]);

  const handleJoin = async () => {
    if (!code) return;
    try {
      await joinMutation.mutateAsync(code);
      navigate(`/session/${code}/vote`, { replace: true });
    } catch { /* handled by mutation */ }
  };

  const apiError = error instanceof ApiError ? error : null;
  const isNotFound = apiError?.status === 404;
  const isSettled = session?.status === "settled" || session?.status === "closed";

  const adminName = useMemo(() => {
    if (!session) return "";
    return session.members.find((m) => m.user_tg_id === session.admin_tg_id)?.display_name ?? "Organizer";
  }, [session]);

  if (isLoading || isAlreadyMember) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-tg-secondary-bg">
        <div className="animate-spin h-8 w-8 border-2 border-tg-button border-t-transparent rounded-full" />
      </div>
    );
  }

  if (isNotFound || (!isLoading && !session)) {
    return <ErrorScreen title="Session not found" subtitle="The link may have expired or been deleted." />;
  }

  if (error && !isNotFound) {
    return <ErrorScreen title="Loading error" subtitle="Could not load session data." />;
  }

  if (isSettled && !isAlreadyMember) {
    return <ErrorScreen title="Voting finished" subtitle="This session is already settled." />;
  }

  return (
    <div className="flex min-h-screen flex-col bg-tg-secondary-bg">
      <Header title="Join Session" showBack={false} />

      <div className="flex-1 flex flex-col items-center justify-center gap-8 px-6">
        {/* Success icon */}
        <div className="flex flex-col items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-success/15">
            <svg className="h-8 w-8 text-success" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-tg-text">You're in!</h2>
          <p className="text-sm text-tg-hint">You've joined the session</p>
        </div>

        {/* Session info card */}
        <Card className="w-full p-5 text-center">
          <p className="text-lg font-semibold text-tg-text mb-1">
            Session #{code}
          </p>
          <p className="text-sm text-tg-hint mb-4">Created by {adminName}</p>
          <div className="flex justify-center gap-6 text-sm text-tg-hint">
            <span>{session?.items.length ?? 0} items</span>
            <span>{session?.members.length ?? 0} joined</span>
          </div>
        </Card>

        <p className="text-sm text-tg-hint">Waiting for admin to start voting...</p>
      </div>

      <CtaBar>
        <Button
          variant="main-action"
          className="w-full"
          disabled={joinMutation.isPending}
          onClick={handleJoin}
        >
          {joinMutation.isPending ? (
            <span className="flex items-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Joining...
            </span>
          ) : (
            "Start Voting"
          )}
        </Button>
      </CtaBar>

      {joinMutation.error && (
        <p className="fixed bottom-20 left-0 right-0 text-center text-sm text-tg-destructive">
          Failed to join. Try again.
        </p>
      )}
    </div>
  );
}

function ErrorScreen({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-tg-secondary-bg px-6">
      <Card className="w-full max-w-sm p-6 text-center">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-tg-destructive/10">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-tg-destructive">
            <circle cx="12" cy="12" r="10" />
            <path d="M15 9l-6 6M9 9l6 6" />
          </svg>
        </div>
        <h2 className="text-lg font-semibold text-tg-text mb-1">{title}</h2>
        <p className="text-sm text-tg-hint">{subtitle}</p>
      </Card>
    </div>
  );
}
