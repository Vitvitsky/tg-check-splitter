import { useState } from "react";
import { BottomSheet, Button } from "@/components/ui";

interface CustomTipSheetProps {
  open: boolean;
  onClose: () => void;
  subtotal: number;
  onApply: (percent: number) => void;
}

export default function CustomTipSheet({ open, onClose, subtotal, onApply }: CustomTipSheetProps) {
  const [percent, setPercent] = useState("");

  const tipAmount = Math.round(subtotal * (parseFloat(percent) || 0) / 100);

  const handleApply = () => {
    onApply(parseInt(percent) || 0);
    onClose();
  };

  return (
    <BottomSheet open={open} onClose={onClose} title="Custom Tip">
      <div className="flex flex-col items-center gap-5 px-4 pb-8">
        <p className="text-sm text-tg-subtitle text-center">
          Enter your desired tip percentage
        </p>

        <div className="flex items-center gap-2 justify-center">
          <input
            className="w-20 px-4 py-3 rounded-[var(--radius-m)] bg-input-bg text-tg-text text-2xl font-semibold text-center outline-none"
            type="number"
            inputMode="numeric"
            min="0"
            max="100"
            value={percent}
            onChange={(e) => setPercent(e.target.value)}
            placeholder="0"
          />
          <span className="text-2xl font-semibold text-tg-hint">%</span>
        </div>

        <p className="text-sm text-tg-subtitle">
          Tip amount: {tipAmount.toLocaleString("ru-RU")} ₽
        </p>

        <Button variant="primary" className="w-full" onClick={handleApply}>
          Apply
        </Button>
      </div>
    </BottomSheet>
  );
}
