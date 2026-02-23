import { useCallback, useState } from "react";

interface QRInviteProps {
  inviteCode: string;
  onClose: () => void;
}

export default function QRInvite({ inviteCode, onClose }: QRInviteProps) {
  const [copied, setCopied] = useState(false);

  const botUsername = "check_splitter_bot"; // TODO: make configurable
  const inviteLink = `https://t.me/${botUsername}?start=${inviteCode}`;

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(inviteLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: select text in a temporary input
      const input = document.createElement("input");
      input.value = inviteLink;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [inviteLink]);

  const handleShare = useCallback(async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: "Разделить чек",
          text: "Присоединяйтесь к разделению чека!",
          url: inviteLink,
        });
      } catch {
        // User cancelled or share failed, do nothing
      }
    } else {
      await handleCopy();
    }
  }, [inviteLink, handleCopy]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md bg-[var(--color-tg-bg)] rounded-t-2xl p-6 pb-10
                    animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Handle bar */}
        <div className="w-10 h-1 bg-[var(--color-tg-hint)]/30 rounded-full mx-auto mb-6" />

        <h2 className="text-lg font-bold text-center mb-2">
          Пригласить участников
        </h2>
        <p className="text-sm text-[var(--color-tg-hint)] text-center mb-6">
          Поделитесь ссылкой, чтобы другие могли присоединиться и выбрать свои
          позиции
        </p>

        {/* Invite link display */}
        <div className="p-3 rounded-xl bg-[var(--color-tg-secondary-bg)] mb-4">
          <p className="text-xs text-[var(--color-tg-hint)] mb-1">
            Ссылка-приглашение
          </p>
          <p className="text-sm font-mono break-all text-[var(--color-tg-text)]">
            {inviteLink}
          </p>
        </div>

        {/* Action buttons */}
        <div className="space-y-3">
          <button
            type="button"
            onClick={handleCopy}
            className="w-full py-3 rounded-xl font-medium transition-colors
                       bg-[var(--color-tg-button)] text-[var(--color-tg-button-text)]
                       active:opacity-80"
          >
            {copied ? "Скопировано!" : "Скопировать ссылку"}
          </button>

          {typeof navigator.share === "function" && (
            <button
              type="button"
              onClick={handleShare}
              className="w-full py-3 rounded-xl font-medium transition-colors
                         bg-[var(--color-tg-secondary-bg)] text-[var(--color-tg-text)]
                         active:opacity-80"
            >
              Поделиться
            </button>
          )}

          <button
            type="button"
            onClick={onClose}
            className="w-full py-3 rounded-xl font-medium transition-colors
                       text-[var(--color-tg-hint)] active:opacity-80"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
}
