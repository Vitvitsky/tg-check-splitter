interface ReceiptItemProps {
  name: string;
  quantity: number;
  price: number;
  onClick?: () => void;
}

export default function ReceiptItem({ name, quantity, price, onClick }: ReceiptItemProps) {
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
          {price.toLocaleString("ru-RU")} ₽
        </span>
      </div>
    </div>
  );
}
