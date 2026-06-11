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
          Ismetlodo panasz jelzes
        </div>
      )}
      {items.length === 0 ? (
        <p className="text-one-grey">Nincs elozmeny.</p>
      ) : (
        <ul className="divide-y divide-one-line">
          {items.map((h, i) => (
            <li key={h.case_id ?? i} className="py-2">
              <div className="flex justify-between items-start gap-2">
                <span className="text-one-grey shrink-0">{h.date}</span>
                <span className="flex-1 min-w-0 truncate font-medium">{h.subject}</span>
                <span className="text-one-grey text-[10px] shrink-0">{h.category}</span>
              </div>
              <div className="mt-1 flex items-start justify-between gap-2 text-[10px] text-one-grey">
                <span className="min-w-0 truncate">{h.excerpt_masked ?? h.case_id ?? ""}</span>
                <span className="shrink-0 rounded border border-one-line bg-one-canvas px-1.5 py-0.5">
                  {h.status}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
