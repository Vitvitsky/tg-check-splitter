interface PhotoPreviewProps {
  photos: File[];
  onRemove: (index: number) => void;
}

export default function PhotoPreview({ photos, onRemove }: PhotoPreviewProps) {
  if (photos.length === 0) return null;

  return (
    <div className="grid grid-cols-3 gap-2">
      {photos.map((file, index) => (
        <div key={`${file.name}-${file.lastModified}-${index}`} className="relative aspect-square">
          <img
            src={URL.createObjectURL(file)}
            alt={`Фото ${index + 1}`}
            className="w-full h-full object-cover rounded-xl"
          />
          <button
            type="button"
            onClick={() => onRemove(index)}
            className="absolute -top-1.5 -right-1.5 w-6 h-6 flex items-center justify-center
                       bg-[var(--color-tg-destructive)] text-white rounded-full text-xs font-bold
                       shadow-md active:scale-90 transition-transform"
            aria-label={`Удалить фото ${index + 1}`}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="1" y1="1" x2="9" y2="9" />
              <line x1="9" y1="1" x2="1" y2="9" />
            </svg>
          </button>
        </div>
      ))}
    </div>
  );
}
