import type { Member } from "@/api/types";

interface ProgressBarProps {
  members: Member[];
}

export default function ProgressBar({ members }: ProgressBarProps) {
  const confirmed = members.filter((m) => m.confirmed).length;
  const total = members.length;
  const percent = total > 0 ? (confirmed / total) * 100 : 0;

  return (
    <div className="space-y-3">
      {/* Bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-[var(--color-tg-text)]">
            Подтвердили: {confirmed}/{total}
          </span>
          <span className="text-[var(--color-tg-hint)]">
            {percent.toFixed(0)}%
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-[var(--color-tg-secondary-bg)]">
          <div
            className="h-full rounded-full bg-[var(--color-tg-button)] transition-all duration-500 ease-out"
            style={{ width: `${percent}%` }}
          />
        </div>
      </div>

      {/* Member list */}
      <div className="flex flex-wrap gap-2">
        {members.map((member) => (
          <span
            key={member.id}
            className={`
              inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium
              transition-colors duration-200
              ${
                member.confirmed
                  ? "bg-green-100 text-green-700"
                  : "bg-[var(--color-tg-secondary-bg)] text-[var(--color-tg-hint)]"
              }
            `}
          >
            {member.confirmed ? (
              <svg
                className="h-3 w-3"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={3}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4.5 12.75l6 6 9-13.5"
                />
              </svg>
            ) : (
              <svg
                className="h-3 w-3"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            )}
            {member.display_name}
          </span>
        ))}
      </div>
    </div>
  );
}
