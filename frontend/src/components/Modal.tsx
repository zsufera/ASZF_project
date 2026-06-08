import { useEffect, useRef } from "react";

interface ModalProps {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}

export function Modal({ title, onClose, children }: ModalProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label={title}>
      <div ref={ref} tabIndex={-1} className="bg-one-surface rounded-one-lg shadow-xl max-w-lg w-full p-6 outline-none animate-fade-in">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-[15px] text-one-ink">{title}</h2>
          <button onClick={onClose} className="text-one-grey hover:text-one-ink text-lg" aria-label="Bezárás">✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}
