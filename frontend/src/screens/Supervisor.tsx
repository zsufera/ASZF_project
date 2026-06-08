import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useSession } from "../state/session";
import { useToast } from "../state/toast";
import { api } from "../lib/api";
import type { SupervisorStats, EscalatedItem } from "../lib/types";
import { KpiGrid } from "../components/KpiCard";

export function Supervisor() {
  const { user } = useSession();
  const navigate = useNavigate();
  const { show } = useToast();

  const [stats, setStats] = useState<SupervisorStats | null>(null);
  const [queue, setQueue] = useState<EscalatedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [auditCaseId, setAuditCaseId] = useState("");
  const [auditResult, setAuditResult] = useState<Record<string, unknown> | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);
  const [purgeLoading, setPurgeLoading] = useState(false);

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
      const res = await api.getAuditCase(auditCaseId, user?.role ?? "supervisor") as Record<string, unknown>;
      setAuditResult(res);
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
      show(dryRun ? `Dry-run: ${JSON.stringify(res)}` : "Purge végrehajtva", dryRun ? "info" : "success");
    } catch (e) {
      show(e instanceof Error ? e.message : "Purge hiba", "error");
    } finally {
      setPurgeLoading(false);
    }
  };

  if (loading) return <div className="text-one-grey p-8">Betöltés…</div>;

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

      {queue.length > 0 && (
        <div className="mb-6">
          <h2 className="text-[13px] font-semibold mb-2">⚠ Eszkalált sor</h2>
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
                    <td className="px-3 py-2">
                      {item.priority === "surgos" ? (
                        <span className="text-status-urgent-fg font-bold">● SÜRGŐS</span>
                      ) : "Normál"}
                    </td>
                    <td className="px-3 py-2 text-one-grey">{item.sla_days_remaining} nap</td>
                    <td className="px-3 py-2">{item.subject}</td>
                    <td className="px-3 py-2">
                      <button
                        onClick={() => navigate(`/case/${item.case_id}`)}
                        className="text-one-turq-d text-[10px] hover:underline"
                      >
                        Megnyitás →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {queue.length === 0 && <p className="text-one-grey text-[12px] mb-6">Nincs eszkalált ügy.</p>}

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-one-surface border border-one-line rounded-one shadow-card p-4">
          <h2 className="text-[13px] font-semibold mb-3">Audit rekord betöltése</h2>
          <form onSubmit={handleAudit} className="flex gap-2 mb-3">
            <input
              value={auditCaseId}
              onChange={(e) => setAuditCaseId(e.target.value)}
              placeholder="Ügy-azonosító"
              className="flex-1 text-[12px] border border-one-line rounded-md px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-one-turq"
              aria-label="Audit ügy-azonosító"
            />
            <button type="submit" disabled={auditLoading} className="bg-one-turq text-[#04201f] font-bold text-[11px] px-3 py-1.5 rounded-pill hover:bg-one-turq-d transition-colors disabled:opacity-50">
              {auditLoading ? "…" : "Betöltés"}
            </button>
          </form>
          {auditResult && (
            <pre className="text-[9px] bg-one-canvas border border-one-line rounded p-2 overflow-auto max-h-48 whitespace-pre-wrap">
              {JSON.stringify(auditResult, null, 2)}
            </pre>
          )}
        </div>

        <div className="bg-one-surface border border-one-line rounded-one shadow-card p-4">
          <h2 className="text-[13px] font-semibold mb-1">Governance — Adatmegőrzési purge</h2>
          <p className="text-one-grey text-[11px] mb-3">Régi ügyrekordok törlése az adatmegőrzési szabályzat szerint.</p>
          <div className="flex gap-2">
            <button
              onClick={() => handlePurge(true)}
              disabled={purgeLoading}
              className="bg-white border border-one-line text-one-ink text-[11px] px-3 py-1.5 rounded-pill hover:bg-one-canvas transition-colors disabled:opacity-50"
            >
              Dry-run
            </button>
            <button
              onClick={() => handlePurge(false)}
              disabled={purgeLoading}
              className="bg-status-urgent-bg text-status-urgent-fg font-bold text-[11px] px-3 py-1.5 rounded-pill hover:opacity-80 transition-opacity disabled:opacity-50"
            >
              {purgeLoading ? "⟳ Purge…" : "Purge végrehajtása"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
