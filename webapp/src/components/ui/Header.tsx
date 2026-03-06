import { useNavigate } from "react-router-dom";

interface HeaderProps {
  title: string;
  showBack?: boolean;
  onBack?: () => void;
  rightIcon?: "pencil" | "none";
  onRightAction?: () => void;
}

export default function Header({ title, showBack = true, onBack, rightIcon, onRightAction }: HeaderProps) {
  const navigate = useNavigate();

  const handleBack = () => {
    if (onBack) onBack();
    else navigate(-1);
  };

  return (
    <header className="sticky top-0 z-40 flex items-center h-14 px-4 bg-tg-header-bg">
      {/* Left: back button */}
      <div className="w-10">
        {showBack && (
          <button type="button" onClick={handleBack} className="p-1 -ml-1 text-tg-accent">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>
        )}
      </div>

      {/* Center: title */}
      <h1 className="flex-1 text-center font-semibold text-base truncate">{title}</h1>

      {/* Right: action */}
      <div className="w-10 flex justify-end">
        {rightIcon === "pencil" && onRightAction && (
          <button type="button" onClick={onRightAction} className="p-1 text-tg-accent">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M17 3a2.85 2.85 0 114 4L7.5 20.5 2 22l1.5-5.5Z" />
            </svg>
          </button>
        )}
      </div>
    </header>
  );
}
