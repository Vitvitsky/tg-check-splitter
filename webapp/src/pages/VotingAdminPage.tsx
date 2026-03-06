import { useCallback, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useSession, useFinishVoting, useRemind } from "@/api/queries";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useTelegramUser, useHaptic } from "@/hooks/useTelegram";
import { Header, Card, SectionLabel, Separator, Badge, Button, CtaBar } from "@/components/ui";
import MemberCardUI from "@/components/ui/MemberCard";

export default function VotingAdminPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const user = useTelegramUser();
  const haptic = useHaptic();

  const { data: session, isLoading, isError } = useSession(code ?? "");
  const sessionId = session?.id ?? "";

  useWebSocket(sessionId || null);

  const finishMutation = useFinishVoting(sessionId);
  const remindMutation = useRemind(sessionId);

  const currentUserId = user?.id ?? 0;
  const [remindedIds, setRemindedIds] = useState<Set<number>>(new Set());

  const handleRemind = useCallback(async (memberTgId: number) => {
    haptic.impactOccurred("light");
    try {
      await remindMutation.mutateAsync(memberTgId);
      setRemindedIds((prev) => new Set(prev).add(memberTgId));
      haptic.notificationOccurred("success");
    } catch {
      haptic.notificationOccurred("error");
    }
  }, [remindMutation, haptic]);

  const handleEndVoting = useCallback(async () => {
    if (!sessionId) return;
    haptic.impactOccurred("medium");
    try {
      await finishMutation.mutateAsync();
      haptic.notificationOccurred("success");
      navigate(`/session/${code}/settle`);
    } catch {
      haptic.notificationOccurred("error");
    }
  }, [sessionId, finishMutation, haptic, navigate, code]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-tg-secondary-bg">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-tg-button border-t-transparent" />
      </div>
    );
  }

  if (isError || !session) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 bg-tg-secondary-bg">
        <p className="text-tg-destructive">Failed to load session</p>
      </div>
    );
  }

  const members = session.members;
  const items = session.items;
  const votedMembers = members.filter((m) =>
    items.some((it) => it.votes.some((v) => v.user_tg_id === m.user_tg_id && v.quantity > 0)),
  );
  const votedCount = votedMembers.length;

  return (
    <div className="flex min-h-screen flex-col bg-tg-secondary-bg">
      <Header title="Voting in Progress" />

      <div className="flex-1 flex flex-col gap-4 p-4 pb-24">
        {/* Progress card */}
        <Card className="p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-base font-semibold text-tg-text">Voting Progress</span>
            <span className="text-lg font-bold text-tg-accent">{votedCount} / {members.length}</span>
          </div>
          <div className="h-2 rounded-full bg-tg-secondary-bg overflow-hidden">
            <div
              className="h-full bg-tg-button rounded-full transition-all duration-500 ease-out"
              style={{ width: `${members.length > 0 ? (votedCount / members.length) * 100 : 0}%` }}
            />
          </div>
          <p className="text-[13px] text-tg-hint mt-2">
            {votedCount} of {members.length} participants have voted
          </p>
        </Card>

        {/* Participants */}
        <SectionLabel>Participants</SectionLabel>
        <Card>
          {members.map((m, i) => {
            const hasVoted = items.some((it) => it.votes.some((v) => v.user_tg_id === m.user_tg_id && v.quantity > 0));
            const isMe = m.user_tg_id === currentUserId;
            return (
              <div key={m.id}>
                {i > 0 && <Separator />}
                <MemberCardUI
                  name={isMe ? `${m.display_name} (you)` : m.display_name}
                  right={
                    <Badge variant={hasVoted ? "success" : "warning"}>
                      {hasVoted ? "Voted" : "Pending"}
                    </Badge>
                  }
                  highlighted={isMe}
                />
              </div>
            );
          })}
        </Card>

        {/* Actions */}
        <SectionLabel>Actions</SectionLabel>
        {members.filter((m) => !items.some((it) => it.votes.some((v) => v.user_tg_id === m.user_tg_id && v.quantity > 0))).map((m) => (
          <Card
            key={m.id}
            className="p-4 flex items-center gap-3 cursor-pointer active:opacity-70"
            onClick={() => handleRemind(m.user_tg_id)}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-tg-hint shrink-0">
              <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 01-3.46 0" />
            </svg>
            <span className="text-[15px] text-tg-text">
              {remindedIds.has(m.user_tg_id) ? `Reminder sent to ${m.display_name}` : `Send Reminder to ${m.display_name}`}
            </span>
            {remindedIds.has(m.user_tg_id) && (
              <svg className="w-4 h-4 text-success ml-auto shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
            )}
          </Card>
        ))}
      </div>

      <CtaBar>
        <Button
          variant="main-action"
          className="w-full"
          disabled={finishMutation.isPending}
          onClick={handleEndVoting}
        >
          {finishMutation.isPending ? "Ending..." : "End Voting"}
        </Button>
      </CtaBar>
    </div>
  );
}
