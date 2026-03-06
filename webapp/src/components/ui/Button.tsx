import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "destructive" | "ghost" | "main-action";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  icon?: ReactNode;
  children: ReactNode;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary: "bg-tg-button text-tg-button-text",
  secondary: "bg-tg-secondary-bg text-tg-text",
  destructive: "bg-tg-destructive text-white",
  ghost: "bg-transparent text-tg-accent",
  "main-action": "bg-tg-button text-tg-button-text shadow-lg",
};

export default function Button({ variant = "primary", icon, children, className = "", ...props }: ButtonProps) {
  const base = "flex items-center justify-center gap-2 rounded-[var(--radius-m)] px-5 py-3 font-semibold text-[15px] transition-opacity active:opacity-80 disabled:opacity-40";
  return (
    <button type="button" className={`${base} ${variantClasses[variant]} ${className}`} {...props}>
      {icon}
      {children}
    </button>
  );
}
