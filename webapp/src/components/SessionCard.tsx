import type { SessionBrief } from "@/api/types";

export interface SessionCardProps {
  session: SessionBrief;
  onClick: () => void;
}

const STATUS_CONFIG: Record<
  string,
  { label: string; dotClass: string; bgClass: string }
> = {
  created: {
    label: "Новый",
    dotClass: "bg-blue-500",
    bgClass: "bg-blue-500/10",
  },
  voting: {
    label: "Голосование",
    dotClass: "bg-amber-500",
    bgClass: "bg-amber-500/10",
  },
  closed: {
    label: "Закрыт",
    dotClass: "bg-purple-500",
    bgClass: "bg-purple-500/10",
  },
  settled: {
    label: "Рассчитан",
    dotClass: "bg-green-500",
    bgClass: "bg-green-500/10",
  },
};

function formatDate(iso: string): string {
  const date = new Date(iso);
  const months = [
    "янв",
    "фев",
    "мар",
    "апр",
    "мая",
    "июн",
    "июл",
    "авг",
    "сен",
    "окт",
    "ноя",
    "дек",
  ];
  const day = date.getDate();
  const month = months[date.getMonth()];
  return `${day} ${month ?? ""}`;
}

export default function SessionCard({ session, onClick }: SessionCardProps) {
  const config = STATUS_CONFIG[session.status] ?? STATUS_CONFIG["created"];

  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center gap-3 rounded-xl bg-[var(--color-tg-section-bg)] p-4 text-left shadow-sm transition-transform active:scale-[0.98]"
    >
      {/* Status dot */}
      <div className="flex flex-col items-center gap-1">
        <span
          className={`h-2.5 w-2.5 rounded-full ${config?.dotClass ?? ""}`}
        />
      </div>

      {/* Center content */}
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-semibold text-[var(--color-tg-text)]">
            #{session.invite_code}
          </span>
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${config?.bgClass ?? ""} ${config?.dotClass.replace("bg-", "text-") ?? ""}`}
          >
            {config?.label ?? session.status}
          </span>
        </div>
        <span className="text-xs text-[var(--color-tg-hint)]">
          {session.member_count}{" "}
          {pluralize(session.member_count, "участник", "участника", "участников")}{" "}
          &middot; {session.item_count}{" "}
          {pluralize(session.item_count, "позиция", "позиции", "позиций")}
        </span>
      </div>

      {/* Date */}
      <span className="shrink-0 text-xs text-[var(--color-tg-hint)]">
        {formatDate(session.created_at)}
      </span>
    </button>
  );
}

function pluralize(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few;
  return many;
}
