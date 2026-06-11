import { useMemo, useState } from "react";
import { api } from "../lib/api";
import type { AcceptanceResult, EvalResult, KpiStatus } from "../lib/types";
import { KpiGrid } from "../components/KpiCard";

const KPI_LABELS: Record<string, string> = {
  faithfulness: "Hitelesség",
  citation_support_rate: "Citáció-támogatás",
  judge_score: "Bíró-pontszám",
  llm_judge_score: "LLM-bíró",
  llm_judge_coverage: "LLM-bíró lefedettség",
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
  const [acceptance, setAcceptance] = useState<AcceptanceResult | null>(null);
  const [acceptanceRunning, setAcceptanceRunning] = useState(false);
  const [error, setError] = useState("");
  const [humanScores, setHumanScores] = useState<Record<string, number>>({});
  const [savingScore, setSavingScore] = useState<string | null>(null);
  const [selectedEmailId, setSelectedEmailId] = useState<string | null>(null);

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setRunning(true);
    setError("");
    setResult(null);
    try {
      const res = await api.runEval({ limit, category: category || undefined, service_provider: provider || undefined, include_edge: includeEdge });
      setResult(res);
      setSelectedEmailId(res.results[0]?.email_id as string | undefined ?? null);
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

  const handleAcceptance = async () => {
    setAcceptanceRunning(true);
    try {
      const res = await api.runAcceptance({ eval_limit: Math.min(limit, 50), include_edge: includeEdge, run_demo: true });
      setAcceptance(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Acceptance hiba");
    } finally {
      setAcceptanceRunning(false);
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

  const judgeAvg = useMemo(() => {
    if (!result) return null;
    const scores = result.results
      .map((r) => r.llm_judge_score)
      .filter((v): v is number => typeof v === "number");
    return scores.length ? scores.reduce((sum, v) => sum + v, 0) / scores.length : null;
  }, [result]);

  const kpiItems = result ? Object.entries(result.kpis.values).map(([k, v]) => ({
    label: KPI_LABELS[k] ?? k,
    value: v !== undefined ? formatVal(k, v) : "-",
    status: (result.kpis.status[k] ?? "green") as KpiStatus,
    target: result.kpis.targets[k],
  })) : [];

  const selectedResult = result?.results.find((item) => item.email_id === selectedEmailId) ?? null;
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
        <button type="submit" disabled={running} className="bg-one-turq text-[#04201f] font-bold text-[12px] px-4 py-2 rounded-pill hover:bg-one-turq-d transition-colors disabled:opacity-50">
          {running ? "Futtatás..." : "Kiértékelés indítása"}
        </button>
        <button type="button" onClick={handleAcceptance} disabled={acceptanceRunning} className="bg-white border border-one-line text-one-ink text-[12px] px-4 py-2 rounded-pill hover:bg-one-canvas transition-colors disabled:opacity-50">
          {acceptanceRunning ? "Acceptance..." : "Acceptance gate"}
        </button>
      </form>

      {error && <div className="text-status-urgent-fg text-[12px] mb-3" role="alert">{error}</div>}
      <AcceptanceGatePanel acceptance={acceptance} />

      {result && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <p className="text-[12px] text-one-grey">Run ID: <code>{result.run_id}</code> · ÁSZF {result.aszf_version}</p>
            <button onClick={handleExport} className="text-[11px] border border-one-line px-3 py-1 rounded-pill hover:bg-one-canvas transition-colors">
              JSON export
            </button>
          </div>

          <KpiGrid items={kpiItems} perRow={4} />
          <HumanScoreSummary scores={humanScores} judgeAvg={judgeAvg} />
          <EvalRegressionDiff diff={result.baseline_diff} />

          <div className="mt-4 grid grid-cols-[1.1fr_0.9fr] gap-4">
            <EvalResultTable
              result={result}
              humanScores={humanScores}
              savingScore={savingScore}
              selectedEmailId={selectedEmailId}
              onSelect={setSelectedEmailId}
              onScore={(emailId, score) => {
                setHumanScores((prev) => ({ ...prev, [emailId]: score }));
                handleHumanScore(emailId, score);
              }}
            />
            <EvalCaseDrilldown item={selectedResult} />
          </div>
        </div>
      )}
    </div>
  );
}

function AcceptanceGatePanel({ acceptance }: { acceptance: AcceptanceResult | null }) {
  if (!acceptance) return null;
  return (
    <div className={`mb-4 rounded-one border p-3 text-[12px] ${acceptance.passed ? "border-kpi-ok bg-[#eefaf4]" : "border-status-esc-fg bg-status-esc-bg"}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="font-semibold">{acceptance.passed ? "Acceptance gate átment" : "Acceptance gate hibát jelzett"}</div>
        {acceptance.eval_run_id ? <code className="text-[10px]">{acceptance.eval_run_id}</code> : null}
      </div>
      {acceptance.kpi_failures.length ? (
        <ul className="mt-2 list-disc pl-5 text-[11px]">
          {acceptance.kpi_failures.map((failure) => <li key={failure}>{failure}</li>)}
        </ul>
      ) : null}
      {acceptance.demo_failures.length ? (
        <ul className="mt-2 list-disc pl-5 text-[11px]">
          {acceptance.demo_failures.map((failure) => <li key={failure}>{failure}</li>)}
        </ul>
      ) : null}
    </div>
  );
}

function EvalRegressionDiff({ diff }: { diff: EvalResult["baseline_diff"] }) {
  if (!diff.has_baseline) return null;
  const entries = Object.entries(diff.diff);
  return (
    <div className="mt-4 bg-one-surface border border-one-line rounded-one p-3 text-[11px]">
      <h3 className="font-semibold mb-2">Baseline különbség</h3>
      <div className="grid grid-cols-3 gap-2">
        {entries.map(([key, value]) => {
          const numeric = typeof value === "number" ? value : Number((value as { delta?: unknown })?.delta ?? 0);
          const status = numeric < 0 ? "romlott" : numeric > 0 ? "javult" : "nincs változás";
          return (
            <div key={key} className="rounded-md border border-one-line bg-one-canvas p-2">
              <div className="font-semibold">{KPI_LABELS[key] ?? key}</div>
              <div className={numeric < 0 ? "text-kpi-bad" : numeric > 0 ? "text-kpi-ok" : "text-one-grey"}>{status}</div>
              <div className="text-one-grey">{String(value)}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function HumanScoreSummary({ scores, judgeAvg }: { scores: Record<string, number>; judgeAvg: number | null }) {
  const values = useMemo(() => Object.values(scores), [scores]);
  if (!values.length) return null;
  const avg = values.reduce((sum, value) => sum + value, 0) / values.length;
  const low = values.filter((value) => value <= 2).length;
  return (
    <div className="mt-4 bg-one-surface border border-one-line rounded-one p-3 text-[12px]">
      Emberi értékelés: <strong>{avg.toFixed(1)}</strong> átlag · {values.length} pontozott eset · {low} alacsony pontszám
      {judgeAvg !== null && (
        <span className="text-one-grey">
          {" "}· LLM-bíró átlag: <strong>{judgeAvg.toFixed(1)}</strong> · eltérés: {avg - judgeAvg >= 0 ? "+" : ""}{(avg - judgeAvg).toFixed(1)}
        </span>
      )}
    </div>
  );
}

function EvalResultTable({
  result,
  humanScores,
  savingScore,
  selectedEmailId,
  onSelect,
  onScore,
}: {
  result: EvalResult;
  humanScores: Record<string, number>;
  savingScore: string | null;
  selectedEmailId: string | null;
  onSelect: (emailId: string) => void;
  onScore: (emailId: string, score: number) => void;
}) {
  return (
    <div className="bg-one-surface border border-one-line rounded-one overflow-hidden">
      <table className="w-full text-[11px]">
        <thead className="bg-one-canvas border-b border-one-line">
          <tr>
            <th className="text-left px-3 py-2 text-one-grey font-semibold">Email ID</th>
            <th className="text-left px-3 py-2 text-one-grey font-semibold">Metrikák</th>
            <th className="text-left px-3 py-2 text-one-grey font-semibold">Emberi értékelés</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-one-line">
          {result.results.map((r) => {
            const emailId = r.email_id as string;
            return (
              <tr key={emailId} className={selectedEmailId === emailId ? "bg-one-turq-l/50" : ""}>
                <td className="px-3 py-2 font-mono text-[10px]">
                  <button onClick={() => onSelect(emailId)} className="hover:text-one-turq-d">{emailId}</button>
                </td>
                <td className="px-3 py-2 text-one-grey">
                  {Object.entries(r).filter(([k]) => k !== "email_id").slice(0, 3).map(([k, v]) => (
                    <span key={k} className="mr-2">{k}: {String(v)}</span>
                  ))}
                </td>
                <td className="px-3 py-2">
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((n) => (
                      <button
                        key={n}
                        onClick={() => onScore(emailId, n)}
                        disabled={savingScore === emailId}
                        className={`w-6 h-6 rounded-full text-[10px] font-bold transition-colors ${humanScores[emailId] === n ? "bg-one-turq text-[#04201f]" : "bg-one-canvas border border-one-line text-one-grey hover:bg-one-turq-l"}`}
                        aria-label={`Pontszám: ${n}`}
                      >
                        {n}
                      </button>
                    ))}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function EvalCaseDrilldown({ item }: { item: EvalResult["results"][number] | null }) {
  if (!item) {
    return (
      <div className="bg-one-surface border border-one-line rounded-one p-3 text-[11px] text-one-grey">
        Válassz egy esetet a részletekhez.
      </div>
    );
  }
  return (
    <div className="bg-one-surface border border-one-line rounded-one p-3 text-[11px]">
      <h3 className="font-semibold mb-2">Bukó-eset drill-down</h3>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
        {Object.entries(item).map(([key, value]) => (
          <div key={key} className="contents">
            <dt className="text-one-grey">{key}</dt>
            <dd className="font-medium break-words">{typeof value === "object" ? JSON.stringify(value) : String(value)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
