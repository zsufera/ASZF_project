import { AlertCircle, AlertTriangle, Clock } from "lucide-react";

interface BadgeProps {
  kind: "category" | "priority" | "confidence" | "escalation" | "sla" | "channel" | "status";
  value: string | number;
}

export function Badge({ kind, value }: BadgeProps) {
  const base = "inline-flex items-center text-[10px] font-bold px-2 py-0.5 rounded-pill select-none";

  if (kind === "priority" && String(value).toLowerCase().includes("sürg")) {
    return <span className={`${base} bg-status-urgent-bg text-status-urgent-fg`} aria-label={`Prioritás: ${value}`}><AlertCircle size={10} className="inline mr-0.5" />{value}</span>;
  }
  if (kind === "escalation") {
    return <span className={`${base} bg-status-esc-bg text-status-esc-fg`} aria-label={`Eszkaláció: ${value}`}><AlertTriangle size={10} className="inline mr-0.5" />{value}</span>;
  }
  if (kind === "confidence") {
    return <span className={`${base} bg-status-conf-bg text-status-conf-fg`} aria-label={`Konfidencia: ${value}`}>Konf {typeof value === "number" ? value.toFixed(2) : value}</span>;
  }
  if (kind === "category") {
    return <span className={`${base} bg-one-turq-l text-one-turq-d`} aria-label={`Kategória: ${value}`}>{value}</span>;
  }
  if (kind === "sla") {
    return <span className={`${base} bg-white border border-one-line text-one-grey`} aria-label={`SLA: ${value} nap`}><Clock size={10} className="inline mr-0.5" />{value} nap</span>;
  }
  if (kind === "channel") {
    return <span className={`${base} bg-one-canvas text-one-grey border border-one-line`} aria-label={`Csatorna: ${value}`}>{value}</span>;
  }
  return <span className={`${base} bg-one-canvas text-one-grey border border-one-line`}>{value}</span>;
}
