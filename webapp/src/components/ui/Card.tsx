import type { KeyboardEvent, ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  /** Set when the card acts as a control (e.g. role="radio" in a pack picker). */
  role?: string;
  ariaChecked?: boolean;
  ariaLabel?: string;
}

export default function Card({
  children,
  className = "",
  onClick,
  role,
  ariaChecked,
  ariaLabel,
}: CardProps) {
  const interactive = Boolean(onClick);

  // A clickable div is unreachable by keyboard unless it is focusable and responds
  // to Enter/Space, so any card with an onClick gets that wiring for free.
  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!onClick) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onClick();
    }
  };

  return (
    <div
      className={`bg-tg-section-bg rounded-[var(--radius-l)] ${interactive ? "active:scale-[0.98] transition-transform cursor-pointer" : ""} ${className}`}
      onClick={onClick}
      onKeyDown={interactive ? handleKeyDown : undefined}
      role={role ?? (interactive ? "button" : undefined)}
      tabIndex={interactive ? 0 : undefined}
      aria-checked={ariaChecked}
      aria-label={ariaLabel}
    >
      {children}
    </div>
  );
}
