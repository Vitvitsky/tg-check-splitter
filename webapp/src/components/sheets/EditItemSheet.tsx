import { useState, useEffect } from "react";
import { BottomSheet, Button } from "@/components/ui";
import type { Item } from "@/api/types";

interface EditItemSheetProps {
  open: boolean;
  onClose: () => void;
  item: Item | null;
  onSave: (id: string, name: string, price: number, quantity: number) => void;
  onDelete: (id: string) => void;
}

export default function EditItemSheet({ open, onClose, item, onSave, onDelete }: EditItemSheetProps) {
  const [name, setName] = useState("");
  const [price, setPrice] = useState("");
  const [qty, setQty] = useState("1");

  useEffect(() => {
    if (item) {
      setName(item.name);
      setPrice(String(item.price));
      setQty(String(item.quantity));
    }
  }, [item]);

  const handleSave = () => {
    if (!item || !name.trim() || !price) return;
    onSave(item.id, name.trim(), parseFloat(price) || 0, parseInt(qty) || 1);
    onClose();
  };

  const handleDelete = () => {
    if (!item) return;
    onDelete(item.id);
    onClose();
  };

  return (
    <BottomSheet open={open} onClose={onClose} title="Edit Item">
      <div className="flex flex-col gap-4 px-4 pb-8">
        <div>
          <label className="text-sm font-medium text-tg-subtitle mb-1 block">Item Name</label>
          <input
            className="w-full px-4 py-3 rounded-[var(--radius-m)] bg-input-bg text-tg-text text-[15px] outline-none"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Item name"
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
        <div className="flex gap-3 mt-2">
          <Button variant="destructive" className="flex-1" onClick={handleDelete}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
            </svg>
            Delete
          </Button>
          <Button variant="primary" className="flex-1" onClick={handleSave}>
            Save
          </Button>
        </div>
      </div>
    </BottomSheet>
  );
}
