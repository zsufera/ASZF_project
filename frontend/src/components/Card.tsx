interface CardProps {
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export function Card({ title, children, className = "" }: CardProps) {
  return (
    <div className={`bg-one-surface border border-one-line rounded-one shadow-card ${className}`}>
      {title && (
        <div className="px-3 pt-3 pb-2 text-[10px] uppercase tracking-wider text-one-grey font-semibold border-b border-one-line">
          {title}
        </div>
      )}
      <div className="p-3">{children}</div>
    </div>
  );
}
