import { useState } from "react";
import { BottomSheet, Button } from "@/components/ui";

interface AddItemSheetProps {
  open: boolean;
  onClose: () => void;
  onAdd: (name: string, price: number, quantity: number) => void;
}

export default function AddItemSheet({ open, onClose, onAdd }: AddItemSheetProps) {
  const [name, setName] = useState("");
  const [price, setPrice] = useState("");
  const [qty, setQty] = useState("1");

  const handleAdd = () => {
    if (!name.trim() || !price) return;
    onAdd(name.trim(), parseFloat(price) || 0, parseInt(qty) || 1);
    setName("");
    setPrice("");
    setQty("1");
    onClose();
  };

  return (
    <BottomSheet open={open} onClose={onClose} title="Add Item">
      <div className="flex flex-col gap-4 px-4 pb-8">
        <div>
          <label className="text-sm font-medium text-tg-subtitle mb-1 block">Item Name</label>
          <input
            className="w-full px-4 py-3 rounded-[var(--radius-m)] bg-input-bg text-tg-text text-[15px] outline-none"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter item name"
          />
        </div>
        <div className="flex gap-3">
          <div className="flex-1">
            <label className="text-sm font-medium text-tg-subtitle mb-1 block">Price</label>
            <input
              className="w-full px-4 py-3 rounded-[var(--radius-m)] bg-input-bg text-tg-text text-[15px] outline-none"
              type="number"
              inputMode="decimal"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="0"
            />
          </div>
          <div className="w-20">
            <label className="text-sm font-medium text-tg-subtitle mb-1 block">Qty</label>
            <input
              className="w-full px-4 py-3 rounded-[var(--radius-m)] bg-input-bg text-tg-text text-[15px] outline-none text-center"
              type="number"
              inputMode="numeric"
              min="1"
              value={qty}
              onChange={(e) => setQty(e.target.value)}
            />
          </div>
        </div>
        <Button variant="primary" className="w-full mt-2" onClick={handleAdd}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
          Add Item
        </Button>
      </div>
    </BottomSheet>
  );
}
