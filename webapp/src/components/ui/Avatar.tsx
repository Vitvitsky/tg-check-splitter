const COLORS = [
  "#3E88F7", "#34C759", "#FF9500", "#AF52DE", "#FF3B30",
  "#5AC8FA", "#FF2D55", "#FFCC00", "#007AFF", "#4CD964",
];

function colorFor(name: string) {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = name.charCodeAt(i) + ((h << 5) - h);
  return COLORS[Math.abs(h) % COLORS.length];
}

interface AvatarProps {
  name: string;
  size?: "sm" | "md";
  className?: string;
}

export default function Avatar({ name, size = "md", className = "" }: AvatarProps) {
  const initial = (name || "?").charAt(0).toUpperCase();
  const bg = colorFor(name);
  const s = size === "sm" ? "w-7 h-7 text-xs" : "w-10 h-10 text-sm";

  return (
    <div
      className={`inline-flex items-center justify-center rounded-full text-white font-semibold shrink-0 ${s} ${className}`}
      style={{ backgroundColor: bg }}
      title={name}
    >
      {initial}
    </div>
  );
}
