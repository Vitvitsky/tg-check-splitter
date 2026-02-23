import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useSession, useUpdateItems } from "@/api/queries";
import EditableItem from "@/components/EditableItem";
import type { EditableItemData } from "@/components/EditableItem";
import QRInvite from "@/components/QRInvite";

export default function EditItemsPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();

  const { data: session, isLoading, error: loadError } = useSession(code ?? "");
  const updateItems = useUpdateItems(session?.id ?? "");

  // Local editable state
  const [items, setItems] = useState<EditableItemData[]>([]);
  const [initialized, setInitialized] = useState(false);
  const [showInvite, setShowInvite] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sync session items into local state once
  useEffect(() => {
    if (session && !initialized) {
      setItems(
        session.items.map((item) => ({
          name: item.name,
          price: item.price,
          quantity: item.quantity,
        })),
      );
      setInitialized(true);
    }
  }, [session, initialized]);

  const handleItemChange = useCallback(
    (index: number, updated: EditableItemData) => {
      setItems((prev) => prev.map((item, i) => (i === index ? updated : item)));
    },
    [],
  );

  const handleItemDelete = useCallback((index: number) => {
    setItems((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleAddItem = useCallback(() => {
    setItems((prev) => [...prev, { name: "Новая позиция", price: 0, quantity: 1 }]);
  }, []);

  const total = useMemo(
    () => items.reduce((sum, item) => sum + item.price * item.quantity, 0),
    [items],
  );

  const handleSave = useCallback(async () => {
    if (!session) return;

    setError(null);

    // Filter out invalid items
    const validItems = items.filter(
      (item) => item.name.trim() && item.price > 0,
    );

    if (validItems.length === 0) {
      setError("Добавьте хотя бы одну позицию с ценой");
      return;
    }

    try {
      await updateItems.mutateAsync(
        validItems.map((item) => ({
          name: item.name.trim(),
          price: item.price,
          quantity: item.quantity,
        })),
      );
      setShowInvite(true);
    } catch {
      setError("Не удалось сохранить позиции. Попробуйте ещё раз.");
    }
  }, [session, items, updateItems]);

  const handleCloseInvite = useCallback(() => {
    setShowInvite(false);
    if (code) {
      navigate(`/session/${code}/vote`);
    }
  }, [code, navigate]);

  const formatPrice = (price: number) =>
    price.toLocaleString("ru-RU", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });

  // --- Loading / Error states ---

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin h-8 w-8 border-2 border-[var(--color-tg-button)] border-t-transparent rounded-full" />
      </div>
    );
  }

  if (loadError || !session) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen p-4 gap-4">
        <p className="text-[var(--color-tg-destructive)] text-center">
          Не удалось загрузить сессию
        </p>
        <button
          type="button"
          onClick={() => navigate("/")}
          className="px-6 py-2 rounded-xl bg-[var(--color-tg-button)] text-[var(--color-tg-button-text)]
                     font-medium active:opacity-80"
        >
          На главную
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-tg-bg)] flex flex-col">
      <div className="p-4 flex-1 pb-36">
        <h1 className="text-xl font-bold mb-4">Редактирование позиций</h1>

        {/* Error message */}
        {error && (
          <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200">
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        )}

        {/* Items list */}
        <div className="space-y-2">
          {items.map((item, index) => (
            <EditableItem
              key={index}
              item={item}
              index={index}
              onChange={handleItemChange}
              onDelete={handleItemDelete}
            />
          ))}
        </div>

        {/* Add item button */}
        <button
          type="button"
          onClick={handleAddItem}
          className="mt-3 w-full py-3 rounded-xl border-2 border-dashed border-[var(--color-tg-hint)]/40
                     flex items-center justify-center gap-2 text-[var(--color-tg-hint)]
                     active:bg-[var(--color-tg-secondary-bg)] transition-colors"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          >
            <line x1="8" y1="2" x2="8" y2="14" />
            <line x1="2" y1="8" x2="14" y2="8" />
          </svg>
          <span className="text-sm font-medium">Добавить позицию</span>
        </button>
      </div>

      {/* Sticky bottom: total + save button */}
      <div className="fixed bottom-0 left-0 right-0 bg-[var(--color-tg-bg)] border-t border-[var(--color-tg-hint)]/10 p-4 pb-8">
        <div className="flex items-center justify-between mb-3">
          <span className="font-bold">Итого</span>
          <span className="font-bold">
            {formatPrice(total)} {session.currency}
          </span>
        </div>
        <button
          type="button"
          onClick={handleSave}
          disabled={items.length === 0 || updateItems.isPending}
          className="w-full py-3 rounded-xl font-medium transition-colors
                     bg-[var(--color-tg-button)] text-[var(--color-tg-button-text)]
                     disabled:opacity-40 active:opacity-80"
        >
          {updateItems.isPending ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-spin h-4 w-4 border-2 border-[var(--color-tg-button-text)] border-t-transparent rounded-full" />
              Сохранение...
            </span>
          ) : (
            "Начать голосование"
          )}
        </button>
      </div>

      {/* Invite modal */}
      {showInvite && code && (
        <QRInvite inviteCode={code} onClose={handleCloseInvite} />
      )}
    </div>
  );
}
