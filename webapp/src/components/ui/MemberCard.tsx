import Avatar from "./Avatar";
import type { ReactNode } from "react";
import { formatMoney } from "@/lib/currency";

interface MemberCardProps {
  name: string;
  subtitle?: string;
  amount?: number;
  currency?: string;
  right?: ReactNode;
  highlighted?: boolean;
}

export default function MemberCard({ name, subtitle, amount, currency = "RUB", right, highlighted }: MemberCardProps) {
  return (
    <div className={`flex items-center gap-3 px-4 py-3 ${highlighted ? "bg-tg-button/5" : ""}`}>
      <Avatar name={name} />
      <div className="flex-1 min-w-0">
        <p className="text-[15px] font-medium text-tg-text truncate">{name}</p>
        {subtitle && <p className="text-[13px] text-tg-hint truncate">{subtitle}</p>}
      </div>
      <div className="shrink-0 flex items-center gap-2">
        {amount !== undefined && (
          <span className="text-[15px] font-semibold text-tg-text whitespace-nowrap">
            {formatMoney(amount, currency)}
          </span>
        )}
        {right}
      </div>
    </div>
  );
}
