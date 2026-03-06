import { useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import { QRCodeSVG } from "qrcode.react";
import { useSession } from "@/api/queries";
import { Header, Card, SectionLabel, Button } from "@/components/ui";

export default function ShareSessionPage() {
  const { code } = useParams<{ code: string }>();
  const { data: session, isLoading } = useSession(code ?? "");
  const [copied, setCopied] = useState(false);

  const botUsername = import.meta.env.VITE_BOT_USERNAME || "serge_w_check_splitter_bot";
  const inviteLink = `https://t.me/${botUsername}?start=${code}`;

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(inviteLink);
    } catch {
      const input = document.createElement("input");
      input.value = inviteLink;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [inviteLink]);

  const handleShare = useCallback(async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title: "Split the bill", text: "Join the check splitting session!", url: inviteLink });
      } catch { /* user cancelled */ }
    } else {
      await handleCopy();
    }
  }, [inviteLink, handleCopy]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-tg-secondary-bg">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-tg-button border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-tg-secondary-bg">
      <Header title="Invite Friends" />

      <div className="flex-1 flex flex-col items-center gap-6 px-4 pt-6">
        {/* QR card */}
        <Card className="w-full flex flex-col items-center gap-5 p-6">
          <SectionLabel>Scan to join</SectionLabel>
          <div className="w-40 h-40 bg-white rounded-[var(--radius-l)] flex items-center justify-center p-2">
            <QRCodeSVG value={inviteLink} size={144} />
          </div>
          <p className="text-sm text-tg-hint">{session?.invite_code ? `Session #${code}` : "Loading..."}</p>
        </Card>

        {/* Invite link */}
        <Card className="w-full p-4">
          <SectionLabel>Invite link</SectionLabel>
          <div className="flex items-center gap-3 mt-2">
            <p className="flex-1 text-sm text-tg-text font-mono break-all">{inviteLink}</p>
            <Button variant="primary" className="shrink-0 px-4 py-2 text-sm" onClick={handleCopy}>
              {copied ? "Copied!" : "Copy"}
            </Button>
          </div>
        </Card>

        {/* Share buttons */}
        <p className="text-sm text-tg-hint">or share directly</p>
        <div className="flex gap-3">
          <Button variant="secondary" className="px-6" onClick={handleShare}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69.01-.03.01-.14-.07-.2-.08-.06-.19-.04-.27-.02-.12.02-1.96 1.25-5.54 3.66-.52.36-1 .53-1.42.52-.47-.01-1.37-.26-2.03-.48-.82-.27-1.47-.42-1.42-.88.03-.24.37-.49 1.02-.75 3.98-1.73 6.63-2.87 7.97-3.44 3.8-1.58 4.59-1.86 5.1-1.87.11 0 .37.03.54.17.14.12.18.28.2.45-.01.06.01.24 0 .37z" />
            </svg>
            Telegram
          </Button>
          <Button variant="secondary" className="px-6" onClick={handleShare}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" />
              <path d="M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98" />
            </svg>
            Share
          </Button>
        </div>
      </div>
    </div>
  );
}
