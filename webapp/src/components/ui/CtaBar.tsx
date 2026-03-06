import type { ReactNode } from "react";

interface CtaBarProps {
  children: ReactNode;
}

export default function CtaBar({ children }: CtaBarProps) {
  return (
    <div className="sticky bottom-0 z-30 bg-tg-bg px-4 pt-3 pb-8">
      {children}
    </div>
  );
}
