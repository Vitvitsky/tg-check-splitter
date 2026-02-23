import { useCallback, useRef, useState } from "react";

export interface EditableItemData {
  name: string;
  price: number;
  quantity: number;
}

interface EditableItemProps {
  item: EditableItemData;
  index: number;
  onChange: (index: number, item: EditableItemData) => void;
  onDelete: (index: number) => void;
}

export default function EditableItem({
  item,
  index,
  onChange,
  onDelete,
}: EditableItemProps) {
  const [editingField, setEditingField] = useState<"name" | "price" | null>(
    null,
  );
  const [nameValue, setNameValue] = useState(item.name);
  const [priceValue, setPriceValue] = useState(item.price.toString());
  const nameInputRef = useRef<HTMLInputElement>(null);
  const priceInputRef = useRef<HTMLInputElement>(null);

  const handleNameClick = useCallback(() => {
    setNameValue(item.name);
    setEditingField("name");
    // Focus after render
    setTimeout(() => nameInputRef.current?.focus(), 0);
  }, [item.name]);

  const handlePriceClick = useCallback(() => {
    setPriceValue(item.price.toString());
    setEditingField("price");
    setTimeout(() => priceInputRef.current?.focus(), 0);
  }, [item.price]);

  const commitName = useCallback(() => {
    const trimmed = nameValue.trim();
    if (trimmed && trimmed !== item.name) {
      onChange(index, { ...item, name: trimmed });
    } else {
      setNameValue(item.name);
    }
    setEditingField(null);
  }, [nameValue, item, index, onChange]);

  const commitPrice = useCallback(() => {
    const parsed = parseFloat(priceValue.replace(",", "."));
    if (!isNaN(parsed) && parsed >= 0 && parsed !== item.price) {
      onChange(index, { ...item, price: parsed });
    } else {
      setPriceValue(item.price.toString());
    }
    setEditingField(null);
  }, [priceValue, item, index, onChange]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, commit: () => void) => {
      if (e.key === "Enter") {
        e.preventDefault();
        commit();
      }
    },
    [],
  );

  return (
    <div className="flex items-center gap-2 p-3 rounded-xl bg-[var(--color-tg-section-bg)]">
      {/* Name */}
      <div className="flex-1 min-w-0">
        {editingField === "name" ? (
          <input
            ref={nameInputRef}
            type="text"
            value={nameValue}
            onChange={(e) => setNameValue(e.target.value)}
            onBlur={commitName}
            onKeyDown={(e) => handleKeyDown(e, commitName)}
            className="w-full text-sm bg-transparent border-b border-[var(--color-tg-button)]
                       outline-none py-0.5 text-[var(--color-tg-text)]"
          />
        ) : (
          <button
            type="button"
            onClick={handleNameClick}
            className="w-full text-left text-sm truncate text-[var(--color-tg-text)]
                       hover:text-[var(--color-tg-accent)] transition-colors"
          >
            {item.name}
          </button>
        )}
      </div>

      {/* Quantity badge (if > 1) */}
      {item.quantity > 1 && (
        <span className="text-xs text-[var(--color-tg-hint)] whitespace-nowrap">
          x{item.quantity}
        </span>
      )}

      {/* Price */}
      <div className="w-24 text-right">
        {editingField === "price" ? (
          <input
            ref={priceInputRef}
            type="number"
            inputMode="decimal"
            step="0.01"
            min="0"
            value={priceValue}
            onChange={(e) => setPriceValue(e.target.value)}
            onBlur={commitPrice}
            onKeyDown={(e) => handleKeyDown(e, commitPrice)}
            className="w-full text-sm text-right bg-transparent border-b border-[var(--color-tg-button)]
                       outline-none py-0.5 text-[var(--color-tg-text)]"
          />
        ) : (
          <button
            type="button"
            onClick={handlePriceClick}
            className="text-sm font-semibold text-[var(--color-tg-text)]
                       hover:text-[var(--color-tg-accent)] transition-colors"
          >
            {item.price.toLocaleString("ru-RU", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </button>
        )}
      </div>

      {/* Delete button */}
      <button
        type="button"
        onClick={() => onDelete(index)}
        className="w-7 h-7 flex items-center justify-center rounded-full
                   text-[var(--color-tg-destructive)] active:bg-[var(--color-tg-secondary-bg)]
                   transition-colors shrink-0"
        aria-label={`Удалить ${item.name}`}
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 14 14"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
        >
          <line x1="2" y1="2" x2="12" y2="12" />
          <line x1="12" y1="2" x2="2" y2="12" />
        </svg>
      </button>
    </div>
  );
}
