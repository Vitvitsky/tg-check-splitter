import type { Share } from "@/api/types";

interface ShareCardProps {
  share: Share;
  isCurrentUser: boolean;
}

export default function ShareCard({ share, isCurrentUser }: ShareCardProps) {
  return (
    <div
      className={`
        flex items-center justify-between rounded-xl p-3 transition-colors duration-150
        ${
          isCurrentUser
            ? "bg-[var(--color-tg-button)]/10 ring-1 ring-[var(--color-tg-button)]/30"
            : "bg-[var(--color-tg-section-bg)]"
        }
      `}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span
            className={`
              truncate text-sm font-medium
              ${isCurrentUser ? "text-[var(--color-tg-button)]" : "text-[var(--color-tg-text)]"}
            `}
          >
            {share.display_name}
          </span>
          {isCurrentUser && (
            <span className="shrink-0 rounded-full bg-[var(--color-tg-button)] px-1.5 py-0.5 text-[10px] font-semibold text-[var(--color-tg-button-text)]">
              вы
            </span>
          )}
        </div>
        <div className="mt-0.5 flex gap-3 text-xs text-[var(--color-tg-hint)]">
          <span>Блюда: {share.dishes_total.toFixed(0)} &#8381;</span>
          {share.tip_amount > 0 && (
            <span>Чаевые: {share.tip_amount.toFixed(0)} &#8381;</span>
          )}
        </div>
      </div>
      <div
        className={`
          text-lg font-bold
          ${isCurrentUser ? "text-[var(--color-tg-button)]" : "text-[var(--color-tg-text)]"}
        `}
      >
        {share.grand_total.toFixed(0)} &#8381;
      </div>
    </div>
  );
}
