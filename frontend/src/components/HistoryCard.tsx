import type { HistoryItem } from "../lib/types";

interface HistoryCardProps {
  items: HistoryItem[];
  isRepeated: boolean;
}

export function HistoryCard({ items, isRepeated }: HistoryCardProps) {
  return (
    <div className="text-[11px]">
      {isRepeated && (
        <div className="text-status-esc-fg bg-status-esc-bg rounded px-2 py-1 mb-2 text-[10px] font-semibold">
          ⚠ Ismétlődő panasz jelzés
        </div>
      )}
      {items.length === 0 ? (
        <p className="text-one-grey">Nincs előzmény.</p>
      ) : (
        <ul className="divide-y divide-one-line">
          {items.map((h, i) => (
            <li key={i} className="py-1.5 flex justify-between items-start gap-2">
              <span className="text-one-grey">{h.date}</span>
              <span className="flex-1 truncate">{h.subject}</span>
              <span className="text-one-grey text-[10px] shrink-0">{h.category}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
