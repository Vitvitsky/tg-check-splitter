import { formatMoney } from "@/lib/currency";

interface ReceiptItemProps {
  name: string;
  quantity: number;
  price: number;
  currency?: string;
  onClick?: () => void;
}

export default function ReceiptItem({ name, quantity, price, currency = "RUB", onClick }: ReceiptItemProps) {
  return (
    <div
      className={`flex items-center justify-between px-4 py-3 ${onClick ? "cursor-pointer active:bg-tg-secondary-bg/50" : ""}`}
      onClick={onClick}
    >
      <span className="text-[15px] text-tg-text truncate mr-3">{name}</span>
      <div className="flex items-center gap-2 shrink-0">
        {quantity > 1 && (
          <span className="text-xs font-medium text-tg-accent">x{quantity}</span>
        )}
        <span className="text-[15px] font-medium text-tg-text whitespace-nowrap">
          {formatMoney(price, currency)}
        </span>
      </div>
    </div>
  );
}
