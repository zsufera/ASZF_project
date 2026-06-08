import { useState } from "react";
import { api } from "../lib/api";
import type { EvalResult, KpiStatus } from "../lib/types";
import { KpiGrid } from "../components/KpiCard";

const KPI_LABELS: Record<string, string> = {
  faithfulness: "Hitelesség",
  citation_support_rate: "Citáció-támogatás",
  judge_score: "Bíró-pontszám",
  coverage: "Lefedettség",
  escalation_appropriateness: "Eszkaláció",
  retrieval_support: "Retrieval",
  time_to_answer_ms_p95: "Idő P95 (ms)",
  out_of_scope_answer_rate: "Hatókörön kívül",
};

function formatVal(key: string, val: number): string {
  if (key === "time_to_answer_ms_p95") return `${val.toFixed(0)} ms`;
  if (val <= 1) return `${(val * 100).toFixed(1)}%`;
  return String(val.toFixed(2));
}

export function Evaluation() {
  const [limit, setLimit] = useState(20);
  const [category, setCategory] = useState("");
  const [provider, setProvider] = useState("");
  const [includeEdge, setIncludeEdge] = useState(false);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<EvalResult | null>(null);
  const [error, setError] = useState("");
  const [humanScores, setHumanScores] = useState<Record<string, number>>({});
  const [savingScore, setSavingScore] = useState<string | null>(null);

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setRunning(true);
    setError("");
    setResult(null);
    try {
      const res = await api.runEval({ limit, category: category || undefined, service_provider: provider || undefined, include_edge: includeEdge });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Hiba");
    } finally {
      setRunning(false);
    }
  };

  const handleHumanScore = async (emailId: string, score: number) => {
    if (!result) return;
    setSavingScore(emailId);
    try {
      await api.setHumanScore({ run_id: result.run_id, email_id: emailId, score });
    } finally {
      setSavingScore(null);
    }
  };

  const handleExport = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `eval-${result.run_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const kpiItems = result ? Object.entries(result.kpis.values).map(([k, v]) => ({
    label: KPI_LABELS[k] ?? k,
    value: v !== undefined ? formatVal(k, v) : "—",
    status: (result.kpis.status[k] ?? "green") as KpiStatus,
    target: result.kpis.targets[k],
  })) : [];

  const inputClass = "text-[12px] border border-one-line rounded-md px-2 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-one-turq";

  return (
    <div>
      <h1 className="text-[16px] font-bold text-one-ink mb-4">Evaluation</h1>

      <form onSubmit={handleRun} className="bg-one-surface border border-one-line rounded-one shadow-card p-4 mb-6 flex flex-wrap gap-3 items-end">
        <div>
          <label className="text-[10px] text-one-grey block mb-1">Limit</label>
          <input type="number" value={limit} onChange={(e) => setLimit(Number(e.target.value))} min={1} max={500} className={`${inputClass} w-20`} aria-label="Limit" />
        </div>
        <div>
          <label className="text-[10px] text-one-grey block mb-1">Kategória</label>
          <input value={category} onChange={(e) => setCategory(e.target.value)} className={`${inputClass} w-36`} placeholder="Összes" aria-label="Kategória" />
        </div>
        <div>
          <label className="text-[10px] text-one-grey block mb-1">Szolgáltató</label>
          <input value={provider} onChange={(e) => setProvider(e.target.value)} className={`${inputClass} w-36`} placeholder="Összes" aria-label="Szolgáltató" />
        </div>
        <div className="flex items-center gap-2">
          <input type="checkbox" id="edge" checked={includeEdge} onChange={(e) => setIncludeEdge(e.target.checked)} className="accent-one-turq" />
          <label htmlFor="edge" className="text-[12px]">Edge esetek</label>
        </div>
        <button
          type="submit"
          disabled={running}
          className="bg-one-turq text-[#04201f] font-bold text-[12px] px-4 py-2 rounded-pill hover:bg-one-turq-d transition-colors disabled:opacity-50"
        >
          {running ? "⟳ Futtatás…" : "Kiértékelés indítása"}
        </button>
      </form>

      {error && <div className="text-status-urgent-fg text-[12px] mb-3" role="alert">{error}</div>}

      {result && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <p className="text-[12px] text-one-grey">Run ID: <code>{result.run_id}</code> · ÁSZF {result.aszf_version}</p>
            <button onClick={handleExport} className="text-[11px] border border-one-line px-3 py-1 rounded-pill hover:bg-one-canvas transition-colors">
              JSON export ↓
            </button>
          </div>

          <KpiGrid items={kpiItems} perRow={4} />

          {result.baseline_diff.has_baseline && (
            <div className="mt-4 bg-one-surface border border-one-line rounded-one p-3 text-[11px]">
              <h3 className="font-semibold mb-2">Baseline különbség</h3>
              <pre className="text-[10px] overflow-auto">{JSON.stringify(result.baseline_diff.diff, null, 2)}</pre>
            </div>
          )}

          <div className="mt-4 bg-one-surface border border-one-line rounded-one overflow-hidden">
            <table className="w-full text-[11px]">
              <thead className="bg-one-canvas border-b border-one-line">
                <tr>
                  <th className="text-left px-3 py-2 text-one-grey font-semibold">Email ID</th>
                  <th className="text-left px-3 py-2 text-one-grey font-semibold">Metrikák</th>
                  <th className="text-left px-3 py-2 text-one-grey font-semibold">Emberi értékelés</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-one-line">
                {result.results.map((r) => (
                  <tr key={r.email_id as string}>
                    <td className="px-3 py-2 font-mono text-[10px]">{r.email_id as string}</td>
                    <td className="px-3 py-2 text-one-grey">
                      {Object.entries(r).filter(([k]) => k !== "email_id").slice(0, 3).map(([k, v]) => (
                        <span key={k} className="mr-2">{k}: {String(v)}</span>
                      ))}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex gap-1">
                        {[1,2,3,4,5].map((n) => (
                          <button
                            key={n}
                            onClick={() => { setHumanScores((p) => ({...p, [r.email_id as string]: n})); handleHumanScore(r.email_id as string, n); }}
                            disabled={savingScore === r.email_id}
                            className={`w-6 h-6 rounded-full text-[10px] font-bold transition-colors ${humanScores[r.email_id as string] === n ? "bg-one-turq text-[#04201f]" : "bg-one-canvas border border-one-line text-one-grey hover:bg-one-turq-l"}`}
                            aria-label={`Pontszám: ${n}`}
                          >
                            {n}
                          </button>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
