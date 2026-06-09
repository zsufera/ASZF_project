import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useSession } from "../state/session";
import { useToast } from "../state/toast";
import { api } from "../lib/api";
import type { AuditCompleteness, AuditEvent, EscalatedItem, SupervisorStats, TraceEvent } from "../lib/types";
import { KpiGrid } from "../components/KpiCard";

export function Supervisor() {
  const { user } = useSession();
  const navigate = useNavigate();
  const { show } = useToast();

  const [stats, setStats] = useState<SupervisorStats | null>(null);
  const [queue, setQueue] = useState<EscalatedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [auditCaseId, setAuditCaseId] = useState("");
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [auditCompleteness, setAuditCompleteness] = useState<AuditCompleteness | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);
  const [purgePreview, setPurgePreview] = useState<Record<string, unknown> | null>(null);
  const [purgeLoading, setPurgeLoading] = useState(false);
  const [traces, setTraces] = useState<TraceEvent[]>([]);

  useEffect(() => {
    if (user?.role !== "supervisor") { navigate("/inbox"); return; }
    Promise.all([api.getSupervisorStats(), api.getSupervisorQueue()])
      .then(([s, q]) => { setStats(s); setQueue(q.items); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user, navigate]);

  const handleAudit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!auditCaseId.trim()) return;
    setAuditLoading(true);
    try {
      const role = user?.role ?? "supervisor";
      const [events, completeness] = await Promise.all([
        api.getAuditEvents({ role, case_id: auditCaseId, limit: 25 }),
        api.getAuditCompleteness(auditCaseId, role),
      ]);
      setAuditEvents(events.events);
      setAuditCompleteness(completeness);
    } catch (e) {
      show(e instanceof Error ? e.message : "Audit hiba", "error");
    } finally {
      setAuditLoading(false);
    }
  };

  const handlePurge = async (dryRun: boolean) => {
    if (!user) return;
    setPurgeLoading(true);
    try {
      const res = await api.purgeGovernance({ dry_run: dryRun, username: user.username, role: user.role });
      setPurgePreview(res);
      show(dryRun ? "Dry-run előnézet frissítve" : "Purge végrehajtva", dryRun ? "info" : "success");
    } catch (e) {
      show(e instanceof Error ? e.message : "Purge hiba", "error");
    } finally {
      setPurgeLoading(false);
    }
  };

  const handleLoadTraces = async () => {
    try {
      const res = await api.getTraces(20);
      setTraces(res.traces);
    } catch (e) {
      show(e instanceof Error ? e.message : "Trace hiba", "error");
    }
  };

  if (loading) return <div className="text-one-grey p-8">Betöltés...</div>;

  const kpiItems = stats ? [
    { label: "Összes ügy", value: stats.total_cases, status: "green" as const },
    { label: "Eszkalált", value: stats.escalated_cases, status: stats.escalated_cases > 5 ? "red" as const : "yellow" as const },
    { label: "Lezárt", value: stats.closed_cases, status: "green" as const },
    { label: "Eszkalációs arány", value: `${(stats.escalation_rate * 100).toFixed(1)}%`, status: stats.escalation_rate > 0.2 ? "red" as const : stats.escalation_rate > 0.1 ? "yellow" as const : "green" as const },
  ] : [];

  return (
    <div>
      <h1 className="text-[16px] font-bold text-one-ink mb-4">Supervisor</h1>

      {stats && (
        <div className="mb-6">
          <KpiGrid items={kpiItems} perRow={4} />
          {stats.by_operator.length > 0 && (
            <div className="mt-4 bg-one-surface border border-one-line rounded-one overflow-hidden">
              <div className="px-3 py-2 border-b border-one-line text-[10px] uppercase text-one-grey font-semibold tracking-wider">Operátoronként</div>
              <table className="w-full text-[12px]">
                <tbody className="divide-y divide-one-line">
                  {stats.by_operator.map((op) => (
                    <tr key={op.username}>
                      <td className="px-3 py-2">{op.username}</td>
                      <td className="px-3 py-2 text-one-grey">{op.processed} ügy</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {queue.length > 0 ? (
        <div className="mb-6">
          <h2 className="text-[13px] font-semibold mb-2">Eszkalált sor</h2>
          <div className="bg-one-surface border border-one-line rounded-one overflow-hidden">
            <table className="w-full text-[11px]">
              <thead className="bg-one-canvas border-b border-one-line">
                <tr>
                  <th className="text-left px-3 py-2 text-one-grey">Ügy ID</th>
                  <th className="text-left px-3 py-2 text-one-grey">Prioritás</th>
                  <th className="text-left px-3 py-2 text-one-grey">SLA</th>
                  <th className="text-left px-3 py-2 text-one-grey">Tárgy</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-one-line">
                {queue.map((item) => (
                  <tr key={item.case_id}>
                    <td className="px-3 py-2 font-mono text-[10px]">{item.case_id}</td>
                    <td className="px-3 py-2">{item.priority === "surgos" ? <span className="text-status-urgent-fg font-bold">SÜRGŐS</span> : "Normál"}</td>
                    <td className="px-3 py-2 text-one-grey">{item.sla_days_remaining} nap</td>
                    <td className="px-3 py-2">{item.subject}</td>
                    <td className="px-3 py-2">
                      <button onClick={() => navigate(`/case/${item.case_id}`)} className="text-one-turq-d text-[10px] hover:underline">Megnyitás</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : <p className="text-one-grey text-[12px] mb-6">Nincs eszkalált ügy.</p>}

      <div className="grid grid-cols-2 gap-4">
        <AuditEventSearch
          caseId={auditCaseId}
          loading={auditLoading}
          events={auditEvents}
          completeness={auditCompleteness}
          onCaseIdChange={setAuditCaseId}
          onSubmit={handleAudit}
        />
        <div className="flex flex-col gap-4">
          <PurgePreview
            loading={purgeLoading}
            preview={purgePreview}
            onDryRun={() => handlePurge(true)}
            onExecute={() => handlePurge(false)}
          />
          <TraceViewer traces={traces} onLoad={handleLoadTraces} />
        </div>
      </div>
    </div>
  );
}

function AuditCompletenessCard({ completeness }: { completeness: AuditCompleteness | null }) {
  if (!completeness) return <p className="text-one-grey text-[11px]">Nincs completeness adat.</p>;
  return (
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
  );
}

function AuditEventSearch({
  caseId,
  loading,
  events,
  completeness,
  onCaseIdChange,
  onSubmit,
}: {
  caseId: string;
  loading: boolean;
  events: AuditEvent[];
  completeness: AuditCompleteness | null;
  onCaseIdChange: (value: string) => void;
  onSubmit: (event: React.FormEvent) => void;
}) {
  return (
    <div className="bg-one-surface border border-one-line rounded-one shadow-card p-4">
      <h2 className="text-[13px] font-semibold mb-3">Audit kereső</h2>
      <form onSubmit={onSubmit} className="flex gap-2 mb-3">
        <input
          value={caseId}
          onChange={(e) => onCaseIdChange(e.target.value)}
          placeholder="Ügy-azonosító"
          className="flex-1 text-[12px] border border-one-line rounded-md px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-one-turq"
          aria-label="Audit ügy-azonosító"
        />
        <button type="submit" disabled={loading} className="bg-one-turq text-[#04201f] font-bold text-[11px] px-3 py-1.5 rounded-pill hover:bg-one-turq-d transition-colors disabled:opacity-50">
          {loading ? "..." : "Betöltés"}
        </button>
      </form>
      <AuditCompletenessCard completeness={completeness} />
      <div className="max-h-60 overflow-auto divide-y divide-one-line">
        {events.length ? events.map((event) => (
          <div key={event.id} className="py-2 text-[11px]">
            <div className="flex justify-between gap-2">
              <span className="font-semibold">{event.event_type}</span>
              <span className="text-one-grey text-[9px]">{event.created_at.slice(0, 16)}</span>
            </div>
            <div className="text-one-grey text-[10px]">{event.actor_username ?? "rendszer"}</div>
          </div>
        )) : <p className="text-one-grey text-[11px]">Nincs betöltött audit esemény.</p>}
      </div>
    </div>
  );
}

function PurgePreview({
  loading,
  preview,
  onDryRun,
  onExecute,
}: {
  loading: boolean;
  preview: Record<string, unknown> | null;
  onDryRun: () => void;
  onExecute: () => void;
}) {
  return (
    <div className="bg-one-surface border border-one-line rounded-one shadow-card p-4">
      <h2 className="text-[13px] font-semibold mb-1">Governance - adatmegőrzési purge</h2>
      <p className="text-one-grey text-[11px] mb-3">Előbb dry-run előnézetet készít, csak utána futtasd a tényleges purge-öt.</p>
      <div className="flex gap-2 mb-3">
        <button onClick={onDryRun} disabled={loading} className="bg-white border border-one-line text-one-ink text-[11px] px-3 py-1.5 rounded-pill hover:bg-one-canvas transition-colors disabled:opacity-50">Dry-run</button>
        <button onClick={onExecute} disabled={loading} className="bg-status-urgent-bg text-status-urgent-fg font-bold text-[11px] px-3 py-1.5 rounded-pill hover:opacity-80 transition-opacity disabled:opacity-50">
          {loading ? "Purge..." : "Purge végrehajtása"}
        </button>
      </div>
      {preview ? (
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[11px]">
          {Object.entries(preview).slice(0, 8).map(([key, value]) => (
            <div key={key} className="contents">
              <dt className="text-one-grey">{key}</dt>
              <dd className="font-medium break-words">{String(value)}</dd>
            </div>
          ))}
        </dl>
      ) : <p className="text-one-grey text-[11px]">Nincs purge előnézet.</p>}
    </div>
  );
}

function TraceViewer({ traces, onLoad }: { traces: TraceEvent[]; onLoad: () => void }) {
  return (
    <div className="bg-one-surface border border-one-line rounded-one shadow-card p-4">
      <div className="flex items-center justify-between gap-2 mb-3">
        <h2 className="text-[13px] font-semibold">Trace viewer</h2>
        <button onClick={onLoad} className="text-one-turq-d text-[10px] hover:underline">Frissítés</button>
      </div>
      <div className="max-h-48 overflow-auto divide-y divide-one-line">
        {traces.length ? traces.map((trace, idx) => (
          <div key={`${trace.created_at}-${idx}`} className="py-2 text-[11px]">
            <div className="flex justify-between gap-2">
              <span className="font-semibold">{trace.name}</span>
              <span className="text-one-grey text-[9px]">{trace.created_at.slice(0, 16)}</span>
            </div>
            <div className="text-one-grey text-[10px]">{trace.case_id ?? "nincs ügy"} · {trace.duration_ms ?? "-"} ms</div>
          </div>
        )) : <p className="text-one-grey text-[11px]">Nincs betöltött trace.</p>}
      </div>
    </div>
  );
}
