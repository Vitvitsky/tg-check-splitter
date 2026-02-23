import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  useCreateSession,
  useUploadPhotos,
  useTriggerOcr,
} from "@/api/queries";
import type { OcrResult } from "@/api/types";
import { resizeImage } from "@/lib/resize";
import PhotoPreview from "@/components/PhotoPreview";

type Stage = "upload" | "processing" | "results";

export default function ScanPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Session creation
  const createSession = useCreateSession();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [inviteCode, setInviteCode] = useState<string | null>(null);

  // Photo state
  const [photos, setPhotos] = useState<File[]>([]);

  // OCR state
  const [stage, setStage] = useState<Stage>("upload");
  const [ocrResult, setOcrResult] = useState<OcrResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Create session on mount
  useEffect(() => {
    if (sessionId) return;
    createSession.mutate("RUB", {
      onSuccess: (session) => {
        setSessionId(session.id);
        setInviteCode(session.invite_code);
      },
      onError: () => {
        setError("Не удалось создать сессию. Попробуйте позже.");
      },
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Mutations (only enabled when sessionId exists)
  const uploadPhotos = useUploadPhotos(sessionId ?? "");
  const triggerOcr = useTriggerOcr(sessionId ?? "");

  const handleFileChange = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const fileList = e.target.files;
      if (!fileList || fileList.length === 0) return;

      setError(null);
      const newFiles: File[] = [];

      for (const file of Array.from(fileList)) {
        try {
          const resized = await resizeImage(file);
          const resizedFile = new File([resized], file.name, {
            type: "image/jpeg",
          });
          newFiles.push(resizedFile);
        } catch {
          // If resize fails, use original
          newFiles.push(file);
        }
      }

      setPhotos((prev) => [...prev, ...newFiles]);

      // Reset input so the same file can be selected again
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    },
    [],
  );

  const handleRemovePhoto = useCallback((index: number) => {
    setPhotos((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleScan = useCallback(async () => {
    if (!sessionId || photos.length === 0) return;

    setError(null);
    setStage("processing");

    try {
      // Upload photos
      await uploadPhotos.mutateAsync(photos);

      // Trigger OCR
      const result = await triggerOcr.mutateAsync();
      setOcrResult(result);
      setStage("results");
    } catch {
      setError("Ошибка при распознавании чека. Попробуйте ещё раз.");
      setStage("upload");
    }
  }, [sessionId, photos, uploadPhotos, triggerOcr]);

  const handleNavigateToEdit = useCallback(() => {
    if (!inviteCode) return;
    navigate(`/session/${inviteCode}/edit`);
  }, [inviteCode, navigate]);

  // Formatting helpers
  const formatPrice = (price: number) =>
    price.toLocaleString("ru-RU", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });

  // --- Render ---

  if (createSession.isPending) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin h-8 w-8 border-2 border-[var(--color-tg-button)] border-t-transparent rounded-full" />
      </div>
    );
  }

  if (stage === "processing") {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4 p-4">
        <div className="animate-spin h-10 w-10 border-3 border-[var(--color-tg-button)] border-t-transparent rounded-full" />
        <p className="text-[var(--color-tg-hint)] text-center">
          Распознаём чек...
        </p>
      </div>
    );
  }

  if (stage === "results" && ocrResult) {
    const itemsTotal = ocrResult.items.reduce(
      (sum, item) => sum + item.price * item.quantity,
      0,
    );

    return (
      <div className="min-h-screen bg-[var(--color-tg-bg)] flex flex-col">
        <div className="p-4 flex-1">
          <h1 className="text-xl font-bold mb-4">Результат распознавания</h1>

          {/* Total mismatch warning */}
          {ocrResult.total_mismatch && (
            <div className="mb-4 p-3 rounded-xl bg-amber-50 border border-amber-200 flex items-start gap-2">
              <svg
                className="w-5 h-5 text-amber-500 mt-0.5 shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"
                />
              </svg>
              <div>
                <p className="text-amber-800 font-medium text-sm">
                  Сумма позиций не совпадает с итогом чека
                </p>
                <p className="text-amber-600 text-xs mt-0.5">
                  Итого в чеке: {formatPrice(ocrResult.total)}{" "}
                  {ocrResult.currency} / Сумма позиций:{" "}
                  {formatPrice(itemsTotal)} {ocrResult.currency}
                </p>
              </div>
            </div>
          )}

          {/* Items list */}
          <div className="space-y-2">
            {ocrResult.items.map((item, index) => (
              <div
                key={`${item.name}-${index}`}
                className="flex items-center justify-between p-3 rounded-xl bg-[var(--color-tg-section-bg)]"
              >
                <div className="flex-1 min-w-0 mr-3">
                  <p className="text-sm font-medium truncate">{item.name}</p>
                  {item.quantity > 1 && (
                    <p className="text-xs text-[var(--color-tg-hint)]">
                      {item.quantity} x {formatPrice(item.price)}{" "}
                      {ocrResult.currency}
                    </p>
                  )}
                </div>
                <p className="text-sm font-semibold whitespace-nowrap">
                  {formatPrice(item.price * item.quantity)} {ocrResult.currency}
                </p>
              </div>
            ))}
          </div>

          {/* Total */}
          <div className="mt-4 flex items-center justify-between p-3 rounded-xl bg-[var(--color-tg-section-bg)] border border-[var(--color-tg-hint)]/20">
            <p className="font-bold">Итого</p>
            <p className="font-bold">
              {formatPrice(itemsTotal)} {ocrResult.currency}
            </p>
          </div>
        </div>

        {/* Bottom buttons */}
        <div className="p-4 pb-8 space-y-3">
          <button
            type="button"
            onClick={handleNavigateToEdit}
            className="w-full py-3 rounded-xl font-medium transition-colors
                       bg-[var(--color-tg-button)] text-[var(--color-tg-button-text)]
                       active:opacity-80"
          >
            Всё верно
          </button>
          <button
            type="button"
            onClick={handleNavigateToEdit}
            className="w-full py-3 rounded-xl font-medium transition-colors
                       bg-[var(--color-tg-secondary-bg)] text-[var(--color-tg-text)]
                       active:opacity-80"
          >
            Редактировать
          </button>
        </div>
      </div>
    );
  }

  // --- Upload stage ---
  return (
    <div className="min-h-screen bg-[var(--color-tg-bg)] flex flex-col">
      <div className="p-4 flex-1">
        <h1 className="text-xl font-bold mb-4">Новый чек</h1>

        {/* Error message */}
        {error && (
          <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200">
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        )}

        {/* Upload area */}
        <label
          className="flex flex-col items-center justify-center gap-3 p-8
                     border-2 border-dashed border-[var(--color-tg-hint)]/40 rounded-xl
                     cursor-pointer active:bg-[var(--color-tg-secondary-bg)] transition-colors"
        >
          <svg
            className="w-12 h-12 text-[var(--color-tg-hint)]"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M6.827 6.175A2.31 2.31 0 015.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 00-1.134-.175 2.31 2.31 0 01-1.64-1.055l-.822-1.316a2.192 2.192 0 00-1.736-1.039 48.774 48.774 0 00-5.232 0 2.192 2.192 0 00-1.736 1.039l-.821 1.316z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M16.5 12.75a4.5 4.5 0 11-9 0 4.5 4.5 0 019 0z"
            />
          </svg>
          <span className="text-[var(--color-tg-hint)] text-sm font-medium">
            Сфотографировать чек
          </span>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            multiple
            onChange={handleFileChange}
            className="hidden"
          />
        </label>

        {/* Gallery button */}
        <label className="mt-3 flex items-center justify-center gap-2 p-3 rounded-xl
                          bg-[var(--color-tg-secondary-bg)] cursor-pointer
                          active:opacity-80 transition-opacity">
          <svg
            className="w-5 h-5 text-[var(--color-tg-hint)]"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"
            />
          </svg>
          <span className="text-sm font-medium text-[var(--color-tg-text)]">
            Выбрать из галереи
          </span>
          <input
            type="file"
            accept="image/*"
            multiple
            onChange={handleFileChange}
            className="hidden"
          />
        </label>

        {/* Photo previews */}
        {photos.length > 0 && (
          <div className="mt-4">
            <p className="text-sm text-[var(--color-tg-hint)] mb-2">
              Загружено фото: {photos.length}
            </p>
            <PhotoPreview photos={photos} onRemove={handleRemovePhoto} />
          </div>
        )}
      </div>

      {/* Bottom button */}
      <div className="p-4 pb-8">
        <button
          type="button"
          onClick={handleScan}
          disabled={photos.length === 0 || !sessionId}
          className="w-full py-3 rounded-xl font-medium transition-colors
                     bg-[var(--color-tg-button)] text-[var(--color-tg-button-text)]
                     disabled:opacity-40 active:opacity-80"
        >
          Распознать
        </button>
      </div>
    </div>
  );
}
