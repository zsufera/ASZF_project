import { useEffect, useState } from "react";
import { ShieldAlert, ShieldCheck } from "lucide-react";
import { api } from "../../lib/api";
import type { AuditCaseRecord, AuditCompleteness } from "../../lib/types";
import { Modal } from "../Modal";

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
  const isSupervisor = role === "supervisor";
  const [record, setRecord] = useState<AuditCaseRecord | null>(null);
  const [completeness, setCompleteness] = useState<AuditCompleteness | null>(null);
  const [error, setError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    let active = true;
    setError("");
    const calls: Array<Promise<unknown>> = [
      api.getAuditCompleteness(caseId, role).then((c) => { if (active) setCompleteness(c); }),
    ];
    if (isSupervisor) {
      calls.push(api.getAuditCase(caseId, role).then((r) => { if (active) setRecord(r); }));
    }
    Promise.all(calls).catch((err) => {
      if (active) setError(err instanceof Error ? err.message : "Audit hiba");
    });
    return () => { active = false; };
  }, [caseId, role, isSupervisor]);

  const complete = completeness?.complete ?? null;
  const tone = complete === null
    ? "border-one-line text-one-grey bg-one-surface"
    : complete
      ? "border-kpi-ok text-kpi-ok bg-[#eefaf4]"
      : "border-status-esc-fg text-status-esc-fg bg-status-esc-bg";
  const Icon = complete === false ? ShieldAlert : ShieldCheck;
  const labelText = complete === null ? "Audit: betöltés…" : complete ? "Audit: teljes" : "Audit: hiányos";

  const chip = (
    <span className={`inline-flex items-center gap-1.5 rounded-pill border px-2.5 py-1 text-[11px] font-semibold ${tone}`}>
      <Icon size={13} /> {labelText}
      {isSupervisor ? <span className="text-[10px] font-normal opacity-70">· részletek</span> : null}
    </span>
  );

  return (
    <div>
      {error ? <p className="text-[11px] text-status-urgent-fg mb-1">{error}</p> : null}
      {isSupervisor ? (
        <button
          onClick={() => setModalOpen(true)}
          className="hover:opacity-80 transition-opacity btn-press"
          aria-label="Audit napló megnyitása"
        >
          {chip}
        </button>
      ) : (
        <span title={completeness && !completeness.complete ? `Hiányzó: ${completeness.missing.join(", ")}` : undefined}>
          {chip}
        </span>
      )}

      {isSupervisor && modalOpen ? (
        <Modal title="Audit napló" onClose={() => setModalOpen(false)}>
          <div className="space-y-3 text-[12px]">
            {completeness ? (
              <div className={`rounded-md border p-2 text-[11px] ${completeness.complete ? "border-kpi-ok bg-[#eefaf4] text-kpi-ok" : "border-status-esc-fg bg-status-esc-bg text-status-esc-fg"}`}>
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
              <div className="space-y-2 max-h-[50vh] overflow-auto">
                {record.events.map((event) => (
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
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
