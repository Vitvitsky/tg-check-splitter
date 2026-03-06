import type { ReactNode } from "react";

type BadgeVariant = "default" | "success" | "warning";

interface BadgeProps {
  variant?: BadgeVariant;
  children: ReactNode;
}

const variants: Record<BadgeVariant, string> = {
  default: "bg-tg-secondary-bg text-tg-hint",
  success: "bg-success/15 text-success",
  warning: "bg-warning/15 text-warning",
};

export default function Badge({ variant = "default", children }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${variants[variant]}`}>
      {children}
    </span>
  );
}
