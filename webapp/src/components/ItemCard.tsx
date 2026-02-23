import { useCallback } from "react";
import type { Item, Member } from "@/api/types";
import MemberBadge from "./MemberBadge";

interface ItemCardProps {
  item: Item;
  members: Member[];
  currentUserId: number;
  myQuantity: number;
  onVote: (itemId: string) => void;
  isVoting: boolean;
}

export default function ItemCard({
  item,
  members,
  currentUserId,
  myQuantity,
  onVote,
  isVoting,
}: ItemCardProps) {
  const handleVote = useCallback(() => {
    if (!isVoting) {
      onVote(item.id);
    }
  }, [item.id, onVote, isVoting]);

  // Total claimed by everyone
  const totalClaimed = item.votes.reduce((sum, v) => sum + v.quantity, 0);
  const remainingSlots = item.quantity - totalClaimed + myQuantity;

  // Other voters (excluding current user)
  const otherVotes = item.votes.filter(
    (v) => v.user_tg_id !== currentUserId && v.quantity > 0,
  );

  // Price per unit
  const unitPrice = item.price / item.quantity;

  return (
    <div className="rounded-xl bg-[var(--color-tg-section-bg)] p-4 transition-shadow duration-150">
      {/* Top row: name + price */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-base font-semibold text-[var(--color-tg-text)]">
            {item.name}
          </h3>
          <div className="mt-0.5 flex items-center gap-2 text-sm text-[var(--color-tg-hint)]">
            <span>{item.price.toFixed(0)} &#8381;</span>
            {item.quantity > 1 && (
              <span className="text-xs">
                ({unitPrice.toFixed(0)} &#8381; &times; {item.quantity})
              </span>
            )}
          </div>
        </div>

        {/* Vote control */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleVote}
            disabled={isVoting}
            className={`
              flex h-9 min-w-[72px] items-center justify-center gap-1.5 rounded-lg
              text-sm font-semibold transition-all duration-150 active:scale-95
              ${
                myQuantity > 0
                  ? "bg-[var(--color-tg-button)] text-[var(--color-tg-button-text)] shadow-sm"
                  : "border border-[var(--color-tg-button)] text-[var(--color-tg-button)] bg-transparent"
              }
              ${isVoting ? "opacity-60" : ""}
            `}
          >
            {myQuantity > 0 ? (
              <>
                <span>{myQuantity}</span>
                <span className="text-xs opacity-80">
                  / {remainingSlots > item.quantity ? item.quantity : item.quantity}
                </span>
              </>
            ) : (
              <span>+</span>
            )}
          </button>
        </div>
      </div>

      {/* Voter badges */}
      {(otherVotes.length > 0 || myQuantity > 0) && (
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {myQuantity > 0 && (
            <MemberBadge
              member={members.find((m) => m.user_tg_id === currentUserId)}
              quantity={myQuantity}
              isCurrentUser={true}
            />
          )}
          {otherVotes.map((vote) => (
            <MemberBadge
              key={vote.id}
              member={members.find((m) => m.user_tg_id === vote.user_tg_id)}
              quantity={vote.quantity}
              isCurrentUser={false}
            />
          ))}
          {/* Capacity indicator */}
          <span className="flex items-center text-xs text-[var(--color-tg-hint)]">
            {totalClaimed}/{item.quantity}
          </span>
        </div>
      )}
    </div>
  );
}
