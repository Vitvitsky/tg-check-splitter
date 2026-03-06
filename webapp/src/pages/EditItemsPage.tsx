import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useSession, useUpdateItems } from "@/api/queries";
import { Header, Card, ReceiptItem, Separator, Button, CtaBar } from "@/components/ui";
import EditItemSheet from "@/components/sheets/EditItemSheet";
import AddItemSheet from "@/components/sheets/AddItemSheet";
import QRInvite from "@/components/QRInvite";
import { formatMoney } from "@/lib/currency";
import type { Item } from "@/api/types";

interface LocalItem {
  id: string;
  name: string;
  price: number;
  quantity: number;
}

export default function EditItemsPage() {
  const { code } = useParams<{ code: string }>();
  const navigate = useNavigate();
  const { data: session, isLoading, error: loadError } = useSession(code ?? "");
  const updateItems = useUpdateItems(session?.id ?? "");

  const [items, setItems] = useState<LocalItem[]>([]);
  const [initialized, setInitialized] = useState(false);
  const [showInvite, setShowInvite] = useState(false);
  const [editingItem, setEditingItem] = useState<LocalItem | null>(null);
  const [showAddSheet, setShowAddSheet] = useState(false);

  useEffect(() => {
    if (session && !initialized) {
      setItems(
        session.items.map((item) => ({
          id: item.id,
          name: item.name,
          price: item.price,
          quantity: item.quantity,
        })),
      );
      setInitialized(true);
    }
  }, [session, initialized]);

  const total = useMemo(
    () => items.reduce((sum, item) => sum + item.price * item.quantity, 0),
    [items],
  );

  const handleEditSave = useCallback(
    (id: string, name: string, price: number, quantity: number) => {
      setItems((prev) =>
        prev.map((item) => (item.id === id ? { ...item, name, price, quantity } : item)),
      );
    },
    [],
  );

  const handleEditDelete = useCallback((id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const handleAdd = useCallback((name: string, price: number, quantity: number) => {
    setItems((prev) => [
      ...prev,
      { id: `new-${Date.now()}`, name, price, quantity },
    ]);
  }, []);

  const handleSave = useCallback(async () => {
    if (!session) return;
    const validItems = items.filter((item) => item.name.trim() && item.price > 0);
    if (validItems.length === 0) return;

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
      // handled by react-query
    }
  }, [session, items, updateItems]);

  const handleCloseInvite = useCallback(() => {
    setShowInvite(false);
    if (code) navigate(`/session/${code}/vote`);
  }, [code, navigate]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin h-8 w-8 border-2 border-tg-button border-t-transparent rounded-full" />
      </div>
    );
  }

  if (loadError || !session) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen p-4 gap-4">
        <p className="text-tg-destructive text-center">Failed to load session</p>
        <Button variant="primary" onClick={() => navigate("/")}>Go Home</Button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-tg-secondary-bg flex flex-col">
      <Header title="Review Receipt" rightIcon="pencil" />

      <div className="flex-1 flex flex-col gap-3 p-4 pb-24">
        {/* Info bar */}
        <div className="flex items-center justify-between py-2">
          <span className="text-[13px] text-tg-hint">{items.length} items recognized</span>
          <span className="text-[13px] font-medium text-tg-text">
            Total: {formatMoney(total, session.currency)}
          </span>
        </div>

        {/* Receipt items */}
        <Card>
          {items.map((item, i) => (
            <div key={item.id}>
              {i > 0 && <Separator />}
              <ReceiptItem
                name={item.name}
                quantity={item.quantity}
                price={item.price * item.quantity}
                currency={session.currency}
                onClick={() => setEditingItem(item)}
              />
            </div>
          ))}
        </Card>

        {/* Add item button */}
        <button
          type="button"
          onClick={() => setShowAddSheet(true)}
          className="flex items-center gap-2 text-tg-accent text-sm font-medium py-2"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
          Add item
        </button>
      </div>

      {/* CTA */}
      <CtaBar>
        <Button
          variant="main-action"
          className="w-full"
          disabled={items.length === 0 || updateItems.isPending}
          onClick={handleSave}
        >
          {updateItems.isPending ? (
            <span className="flex items-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Saving...
            </span>
          ) : (
            "Share & Start Voting"
          )}
        </Button>
      </CtaBar>

      {/* Edit Item Sheet */}
      <EditItemSheet
        open={!!editingItem}
        onClose={() => setEditingItem(null)}
        item={editingItem as Item | null}
        onSave={handleEditSave}
        onDelete={handleEditDelete}
      />

      {/* Add Item Sheet */}
      <AddItemSheet
        open={showAddSheet}
        onClose={() => setShowAddSheet(false)}
        onAdd={handleAdd}
      />

      {/* Invite modal */}
      {showInvite && code && (
        <QRInvite inviteCode={code} onClose={handleCloseInvite} />
      )}
    </div>
  );
}
