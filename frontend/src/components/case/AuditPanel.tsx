import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { AuditCaseRecord, AuditCompleteness } from "../../lib/types";
import { Card } from "../Card";

interface AuditPanelProps {
  caseId: string;
  role: string;
}

function shortPayload(payload: Record<string, unknown>): string {
  const keys = Object.keys(payload).slice(0, 3);
  if (!keys.length) return "nincs részlet";
  return keys.map((key) => `${key}: ${String(payload[key])}`).join(" · ");
}

export function AuditPanel({ caseId, role }: AuditPanelProps) {
  const [record, setRecord] = useState<AuditCaseRecord | null>(null);
  const [completeness, setCompleteness] = useState<AuditCompleteness | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setError("");
    Promise.all([
      api.getAuditCase(caseId, role),
      api.getAuditCompleteness(caseId, role),
    ])
      .then(([auditRecord, auditCompleteness]) => {
        if (!active) return;
        setRecord(auditRecord);
        setCompleteness(auditCompleteness);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Audit hiba");
      });
    return () => { active = false; };
  }, [caseId, role]);

  return (
    <Card title="Audit">
      {error ? <p className="text-[11px] text-status-urgent-fg">{error}</p> : null}
      {completeness ? (
        <div className={`mb-3 rounded-md border p-2 text-[11px] ${completeness.complete ? "border-kpi-ok bg-[#eefaf4] text-kpi-ok" : "border-status-esc-fg bg-status-esc-bg text-status-esc-fg"}`}>
          <div className="font-semibold">{completeness.complete ? "Audit teljes" : "Audit hiányos"}</div>
          {!completeness.complete ? (
            <div className="mt-1 flex flex-wrap gap-1">
              {completeness.missing.map((item) => (
                <span key={item} className="rounded-full bg-white/70 px-2 py-0.5 text-[10px]">{item}</span>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
      {record?.events?.length ? (
        <div className="space-y-2">
          {record.events.slice(0, 5).map((event) => (
            <div key={event.id} className="border-l-2 border-one-line pl-2 text-[11px]">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-one-ink">{event.event_type}</span>
                <span className="text-[9px] text-one-grey">{event.created_at.slice(0, 16)}</span>
              </div>
              <div className="text-[10px] text-one-grey">{event.actor_username ?? "rendszer"}</div>
              <div className="text-[10px] text-one-grey">{shortPayload(event.payload)}</div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-one-grey text-[11px]">Nincs audit esemény.</p>
      )}
    </Card>
  );
}
