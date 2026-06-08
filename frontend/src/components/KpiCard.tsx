import type { KpiStatus } from "../lib/types";

interface KpiCardProps {
  label: string;
  value: string | number;
  status: KpiStatus;
  target?: number;
}

const BAR: Record<KpiStatus, string> = {
  green: "bg-kpi-ok",
  yellow: "bg-kpi-warn",
  red: "bg-kpi-bad",
};

export function KpiCard({ label, value, status, target }: KpiCardProps) {
  return (
    <div className="bg-one-surface border border-one-line rounded-one shadow-card overflow-hidden">
      <div className={`h-1 ${BAR[status]}`} />
      <div className="px-3 py-3">
        <div className="text-[10px] text-one-grey uppercase tracking-wider mb-1">{label}</div>
        <div className="text-xl font-bold text-one-ink">{value}</div>
        {target !== undefined && (
          <div className="text-[10px] text-one-grey mt-0.5">Cél: {target}</div>
        )}
      </div>
    </div>
  );
}

interface KpiGridProps {
  items: Array<{ label: string; value: string | number; status: KpiStatus; target?: number }>;
  perRow?: number;
}

export function KpiGrid({ items, perRow = 4 }: KpiGridProps) {
  return (
    <div
      className="grid gap-3"
      style={{ gridTemplateColumns: `repeat(${perRow}, minmax(0, 1fr))` }}
    >
      {items.map((item, i) => (
        <KpiCard key={i} {...item} />
      ))}
    </div>
  );
}
