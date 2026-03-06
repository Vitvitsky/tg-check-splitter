interface SectionLabelProps {
  children: string;
}

export default function SectionLabel({ children }: SectionLabelProps) {
  return (
    <span className="text-[13px] font-semibold text-tg-section-header">
      {children}
    </span>
  );
}
