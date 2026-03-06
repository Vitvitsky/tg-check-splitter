import { useState } from "react";
import { BottomSheet, Button } from "@/components/ui";
import type { Item } from "@/api/types";

interface AddGuestSheetProps {
  open: boolean;
  onClose: () => void;
  items: Item[];
  onAdd: (name: string, itemIds: string[]) => void;
}

export default function AddGuestSheet({ open, onClose, items, onAdd }: AddGuestSheetProps) {
  const [name, setName] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleAdd = () => {
    if (!name.trim()) return;
    onAdd(name.trim(), Array.from(selected));
    setName("");
    setSelected(new Set());
    onClose();
  };

  return (
    <BottomSheet open={open} onClose={onClose} title="Add Guest">
      <div className="flex flex-col gap-4 px-4 pb-8">
        <div>
          <label className="text-sm font-medium text-tg-subtitle mb-1 block">Guest Name</label>
          <input
            className="w-full px-4 py-3 rounded-[var(--radius-m)] bg-input-bg text-tg-text text-[15px] outline-none"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter name"
          />
        </div>

        <div>
          <label className="text-sm font-medium text-tg-subtitle mb-2 block">Select Dishes</label>
          <div className="rounded-[var(--radius-l)] bg-input-bg overflow-hidden">
            {items.map((item, i) => (
              <label
                key={item.id}
                className={`flex items-center gap-3 px-4 py-3 cursor-pointer ${i > 0 ? "border-t border-separator" : ""}`}
              >
                <input
                  type="checkbox"
                  checked={selected.has(item.id)}
                  onChange={() => toggle(item.id)}
                  className="w-5 h-5 rounded accent-[var(--color-tg-button)]"
                />
                <span className="flex-1 text-[15px] text-tg-text">{item.name}</span>
                <span className="text-[15px] text-tg-hint">{item.price.toLocaleString("ru-RU")} ₽</span>
              </label>
            ))}
          </div>
        </div>

        <Button variant="primary" className="w-full" onClick={handleAdd}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4-4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M19 8v6M22 11h-6" />
          </svg>
          Add Guest
        </Button>
      </div>
    </BottomSheet>
  );
}
