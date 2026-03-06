import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCreateSession, useUploadPhotos, useTriggerOcr } from "@/api/queries";
import type { OcrResult } from "@/api/types";
import { resizeImage } from "@/lib/resize";
import { Header, Card, ReceiptItem, Separator, Button, CtaBar } from "@/components/ui";
import PhotoPreview from "@/components/PhotoPreview";

type Stage = "upload" | "processing" | "results";

export default function ScanPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const galleryInputRef = useRef<HTMLInputElement>(null);

  const createSession = useCreateSession();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [inviteCode, setInviteCode] = useState<string | null>(null);
  const [photos, setPhotos] = useState<File[]>([]);
  const [stage, setStage] = useState<Stage>("upload");
  const [ocrResult, setOcrResult] = useState<OcrResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (sessionId) return;
    createSession.mutate("RUB", {
      onSuccess: (session) => { setSessionId(session.id); setInviteCode(session.invite_code); },
      onError: () => setError("Failed to create session"),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const uploadPhotos = useUploadPhotos(sessionId ?? "");
  const triggerOcr = useTriggerOcr(sessionId ?? "");

  const handleFileChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;
    setError(null);
    const newFiles: File[] = [];
    for (const file of Array.from(fileList)) {
      try {
        const resized = await resizeImage(file);
        newFiles.push(new File([resized], file.name, { type: "image/jpeg" }));
      } catch { newFiles.push(file); }
    }
    setPhotos((prev) => [...prev, ...newFiles]);
    e.target.value = "";
  }, []);

  const handleRemovePhoto = useCallback((index: number) => {
    setPhotos((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleScan = useCallback(async () => {
    if (!sessionId || photos.length === 0) return;
    setError(null);
    setStage("processing");
    try {
      await uploadPhotos.mutateAsync(photos);
      const result = await triggerOcr.mutateAsync();
      setOcrResult(result);
      setStage("results");
    } catch {
      setError("Failed to recognize receipt. Try again.");
      setStage("upload");
    }
  }, [sessionId, photos, uploadPhotos, triggerOcr]);

  const handleNavigateToEdit = useCallback(() => {
    if (inviteCode) navigate(`/session/${inviteCode}/edit`);
  }, [inviteCode, navigate]);

  if (createSession.isPending) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-tg-secondary-bg">
        <div className="animate-spin h-8 w-8 border-2 border-tg-button border-t-transparent rounded-full" />
      </div>
    );
  }

  // --- Processing stage ---
  if (stage === "processing") {
    return (
      <div className="flex min-h-screen flex-col bg-tg-secondary-bg">
        <Header title="Processing" showBack={false} />
        <div className="flex-1 flex flex-col items-center justify-center gap-8 p-10">
          <div className="animate-spin h-12 w-12 border-3 border-tg-button border-t-transparent rounded-full" />
          <div className="text-center">
            <h2 className="text-xl font-bold text-tg-text mb-2">Recognizing receipt...</h2>
            <p className="text-sm text-tg-hint">This may take a few seconds</p>
          </div>
          <div className="w-full max-w-xs">
            <div className="h-1.5 rounded-full bg-tg-secondary-bg overflow-hidden">
              <div className="h-full bg-tg-button rounded-full animate-pulse" style={{ width: "60%" }} />
            </div>
            <p className="text-xs text-tg-hint text-center mt-2">Extracting items from photo...</p>
          </div>
        </div>
      </div>
    );
  }

  // --- Results stage ---
  if (stage === "results" && ocrResult) {
    const itemsTotal = ocrResult.items.reduce((sum, item) => sum + item.price * item.quantity, 0);
    const hasMismatch = ocrResult.total_mismatch;

    return (
      <div className="min-h-screen bg-tg-secondary-bg flex flex-col">
        <Header title="Review Receipt" rightIcon="pencil" onRightAction={handleNavigateToEdit} />

        <div className="flex-1 flex flex-col gap-3 p-4 pb-24">
          {hasMismatch && (
            <div className="flex items-start gap-2.5 rounded-[var(--radius-m)] bg-warning/10 p-3">
              <svg className="w-5 h-5 text-warning shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <div>
                <p className="text-sm font-medium text-warning">Total mismatch detected</p>
                <p className="text-xs text-tg-hint mt-0.5">
                  Items sum: {itemsTotal.toLocaleString("ru-RU")} ₽ vs Receipt: {ocrResult.total.toLocaleString("ru-RU")} ₽
                </p>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between py-2">
            <span className="text-[13px] text-tg-hint">{ocrResult.items.length} items recognized</span>
            <span className="text-[13px] font-medium text-tg-text">Total: {ocrResult.total.toLocaleString("ru-RU")} ₽</span>
          </div>

          <Card>
            {ocrResult.items.map((item, i) => (
              <div key={`${item.name}-${i}`}>
                {i > 0 && <Separator />}
                <ReceiptItem name={item.name} quantity={item.quantity} price={item.price * item.quantity} />
              </div>
            ))}
          </Card>
        </div>

        <CtaBar>
          <Button variant="main-action" className="w-full" onClick={handleNavigateToEdit}>
            Share & Start Voting
          </Button>
        </CtaBar>
      </div>
    );
  }

  // --- Upload stage ---
  return (
    <div className="min-h-screen bg-tg-secondary-bg flex flex-col">
      <Header title="New Check" />

      <div className="flex-1 flex flex-col items-center gap-6 p-4 pt-10">
        {error && (
          <div className="w-full p-3 rounded-[var(--radius-m)] bg-tg-destructive/10 text-sm text-tg-destructive">
            {error}
          </div>
        )}

        {/* Camera area */}
        {photos.length === 0 ? (
          <div className="w-full flex flex-col items-center justify-center gap-4 h-80 rounded-[var(--radius-xl)] bg-input-bg">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-tg-hint">
              <path d="M14.5 4h-5L7 7H4a2 2 0 00-2 2v9a2 2 0 002 2h16a2 2 0 002-2V9a2 2 0 00-2-2h-3l-2.5-3z" />
              <circle cx="12" cy="13" r="3" />
            </svg>
            <p className="text-sm font-medium text-tg-text">Take a photo of the receipt</p>
            <p className="text-xs text-tg-hint">Or upload from gallery</p>
          </div>
        ) : (
          <PhotoPreview photos={photos} onRemove={handleRemovePhoto} />
        )}

        {/* Action buttons */}
        <div className="w-full flex flex-col items-center gap-3">
          <Button variant="primary" className="w-full" onClick={() => fileInputRef.current?.click()}>
            Take Photo
          </Button>
          <input ref={fileInputRef} type="file" accept="image/*" capture="environment" multiple onChange={handleFileChange} className="hidden" />

          <button
            type="button"
            onClick={() => galleryInputRef.current?.click()}
            className="flex items-center gap-2 text-sm font-medium text-tg-text"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <path d="M21 15l-5-5L5 21" />
            </svg>
            Choose from Gallery
          </button>
          <input ref={galleryInputRef} type="file" accept="image/*" multiple onChange={handleFileChange} className="hidden" />
        </div>
      </div>

      {photos.length > 0 && (
        <CtaBar>
          <Button variant="main-action" className="w-full" disabled={!sessionId} onClick={handleScan}>
            Recognize Receipt
          </Button>
        </CtaBar>
      )}
    </div>
  );
}
