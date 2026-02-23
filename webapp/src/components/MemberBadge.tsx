import type { Member } from "@/api/types";

interface MemberBadgeProps {
  member: Member | undefined;
  quantity: number;
  isCurrentUser: boolean;
}

export default function MemberBadge({
  member,
  quantity,
  isCurrentUser,
}: MemberBadgeProps) {
  const name = member?.display_name ?? "?";
  const initial = name.charAt(0).toUpperCase();

  return (
    <span
      className={`
        inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-medium
        transition-colors duration-150
        ${
          isCurrentUser
            ? "bg-[var(--color-tg-button)] text-[var(--color-tg-button-text)]"
            : "bg-[var(--color-tg-secondary-bg)] text-[var(--color-tg-hint)]"
        }
      `}
      title={name}
    >
      <span className="font-semibold">{initial}</span>
      {quantity > 1 && <span>&times;{quantity}</span>}
    </span>
  );
}
