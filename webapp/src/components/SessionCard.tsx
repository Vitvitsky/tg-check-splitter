import type { SessionBrief } from "@/api/types";

export interface SessionCardProps {
  session: SessionBrief;
  onClick: () => void;
}

function pluralize(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few;
  return many;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${months[d.getMonth()]} ${d.getDate()}`;
}

const STATUS_ICON: Record<string, string> = {
  created: "📝",
  voting: "🗳",
  closed: "✅",
  settled: "🟢",
};

export default function SessionCard({ session, onClick }: SessionCardProps) {
  const name = `Session #${session.invite_code}`;
  const icon = STATUS_ICON[session.status] ?? "📝";
  const subtitle = `${session.member_count} ${pluralize(session.member_count, "person", "people", "people")} · ${session.item_count} items`;
  return (
    <div onClick={onClick} className="cursor-pointer active:scale-[0.98] transition-transform">
      <div className="flex items-center gap-3 px-4 py-3">
        <span className="text-xl shrink-0">{icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-[15px] font-medium text-tg-text truncate">{name}</p>
          <p className="text-[13px] text-tg-hint">
            {subtitle}
            {session.status === "settled" && ` · ${formatDate(session.created_at)}`}
          </p>
        </div>
      </div>
    </div>
  );
}

