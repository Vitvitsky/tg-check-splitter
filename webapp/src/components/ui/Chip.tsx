interface ChipProps {
  label: string;
  active?: boolean;
  onClick?: () => void;
}

export default function Chip({ label, active = false, onClick }: ChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`
        px-4 py-1.5 rounded-full text-sm font-medium transition-colors
        ${active
          ? "bg-tg-button text-tg-button-text"
          : "bg-tg-secondary-bg text-tg-text"
        }
      `}
    >
      {label}
    </button>
  );
}
