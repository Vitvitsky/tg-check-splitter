import { useCallback } from "react";

const PRESETS = [0, 5, 10, 15, 20, 25] as const;

interface TipSliderProps {
  value: number;
  onChange: (value: number) => void;
}

export default function TipSlider({ value, onChange }: TipSliderProps) {
  const handleSlider = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange(Number(e.target.value));
    },
    [onChange],
  );

  return (
    <div className="space-y-4">
      {/* Preset pills */}
      <div className="flex flex-wrap gap-2">
        {PRESETS.map((preset) => (
          <button
            key={preset}
            onClick={() => onChange(preset)}
            className={`
              rounded-full px-4 py-1.5 text-sm font-medium transition-all duration-150
              active:scale-95
              ${
                value === preset
                  ? "bg-[var(--color-tg-button)] text-[var(--color-tg-button-text)] shadow-sm"
                  : "bg-[var(--color-tg-secondary-bg)] text-[var(--color-tg-text)]"
              }
            `}
          >
            {preset}%
          </button>
        ))}
      </div>

      {/* Range slider */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <span className="text-xs text-[var(--color-tg-hint)]">0%</span>
          <span className="text-sm font-semibold text-[var(--color-tg-button)]">
            {value}%
          </span>
          <span className="text-xs text-[var(--color-tg-hint)]">25%</span>
        </div>
        <input
          type="range"
          min={0}
          max={25}
          step={1}
          value={value}
          onChange={handleSlider}
          className="w-full accent-[var(--color-tg-button)]"
        />
      </div>
    </div>
  );
}
