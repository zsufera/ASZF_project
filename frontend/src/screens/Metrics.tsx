import { useCallback, useEffect, useState } from "react";
import { KpiGrid } from "../components/KpiCard";
import { api } from "../lib/api";
import { FEEDBACK_REASON_LABELS } from "../lib/feedbackReasons";
import type { KpiStatus, OperationalMetrics } from "../lib/types";

function pct(value: number | null): string {
  return value === null ? "-" : `${(value * 100).toFixed(1)}%`;
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "-";
  if (seconds < 60) return `${seconds.toFixed(0)} mp`;
  return `${(seconds / 60).toFixed(1)} perc`;
}

export function Metrics() {
  const [metrics, setMetrics] = useState<OperationalMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setMetrics(await api.getOperationalMetrics());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Nem sikerult betolteni a mereseket");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (!metrics) {
    return (
      <div>
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-[16px] font-bold text-one-ink">Visszameres</h1>
          <button
            onClick={load}
            disabled={loading}
            className="text-[11px] border border-one-line px-3 py-1 rounded-pill hover:bg-one-canvas transition-colors disabled:opacity-50"
          >
            Frissites
          </button>
        </div>
        {error ? (
          <div className="text-status-urgent-fg text-[12px]" role="alert">{error}</div>
        ) : (
          <div className="text-[12px] text-one-grey">{loading ? "Betoltes..." : "Nincs megjelenitheto adat."}</div>
        )}
      </div>
    );
  }

  const { case_funnel, handling_time, draft_acceptance, feedback, escalation } = metrics;
  const kpiItems = [
    {
      label: "Copilot-lefedettseg",
      value: pct(case_funnel.adoption_rate),
      status: (case_funnel.adoption_rate >= 0.7 ? "green" : case_funnel.adoption_rate >= 0.4 ? "yellow" : "red") as KpiStatus,
    },
    {
      label: "Atlagos atfutasi ido",
      value: formatDuration(handling_time.avg_seconds),
      status: (handling_time.avg_seconds === null || handling_time.avg_seconds <= 300 ? "green" : "yellow") as KpiStatus,
    },
    {
      label: "Pozitiv visszajelzes",
      value: pct(feedback.positive_rate),
      status: (feedback.positive_rate === null || feedback.positive_rate >= 0.75 ? "green" : feedback.positive_rate >= 0.5 ? "yellow" : "red") as KpiStatus,
    },
    {
      label: "Eszkalacios arany",
      value: pct(escalation.escalation_rate),
      status: (escalation.escalation_rate > 0.1 ? "yellow" : "green") as KpiStatus,
    },
    {
      label: "Lezart ugyek",
      value: case_funnel.closed_cases,
      status: "green" as KpiStatus,
    },
    {
      label: "Draft mintak",
      value: draft_acceptance.sample_size,
      status: "green" as KpiStatus,
    },
    {
      label: "Rossz forras jelzes",
      value: feedback.wrong_source,
      status: (feedback.wrong_source > 3 ? "yellow" : "green") as KpiStatus,
    },
    {
      label: "Osszes ugy",
      value: case_funnel.total_cases,
      status: "green" as KpiStatus,
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-[16px] font-bold text-one-ink">Visszameres</h1>
        <button
          onClick={load}
          disabled={loading}
          className="text-[11px] border border-one-line px-3 py-1 rounded-pill hover:bg-one-canvas transition-colors disabled:opacity-50"
        >
          {loading ? "Frissites..." : "Frissites"}
        </button>
      </div>
      <p className="text-[12px] text-one-grey mb-4">
        Elo mukodesi mutatok a feldolgozott ugyek audit-naplojabol.
      </p>
      {error && <div className="text-status-urgent-fg text-[12px] mb-3" role="alert">{error}</div>}

      <KpiGrid items={kpiItems} perRow={4} />

      <div className="mt-4 grid grid-cols-2 gap-4">
        <DraftAcceptanceCard acceptance={draft_acceptance} />
        <HandlingTimeCard handling={handling_time} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4">
        <FeedbackByCategoryCard items={feedback.by_category} />
        <FeedbackReasonsCard byReason={feedback.by_reason} />
      </div>
    </div>
  );
}

function DraftAcceptanceCard({ acceptance }: { acceptance: OperationalMetrics["draft_acceptance"] }) {
  const total = acceptance.sample_size;
  const segments = [
    { key: "unchanged", label: "Valtoztatas nelkul", count: acceptance.unchanged, color: "bg-kpi-ok" },
    { key: "light_edit", label: "Kis szerkesztes", count: acceptance.light_edit, color: "bg-kpi-warn" },
    { key: "rewrite", label: "Ujrairas", count: acceptance.rewrite, color: "bg-kpi-bad" },
  ];
  return (
    <div className="bg-one-surface border border-one-line rounded-one shadow-card p-4">
      <h2 className="text-[13px] font-semibold mb-1">Draft-atvetel megoszlasa</h2>
      <p className="text-[11px] text-one-grey mb-3">
        Elso draft es vegleges szoveg elterese ({total} lezart ugy).
      </p>
      {total ? (
        <>
          <div className="flex h-3 rounded-full overflow-hidden border border-one-line">
            {segments.filter((s) => s.count > 0).map((s) => (
              <div
                key={s.key}
                className={s.color}
                style={{ width: `${(s.count / total) * 100}%` }}
                title={`${s.label}: ${s.count}`}
              />
            ))}
          </div>
          <div className="mt-2 flex flex-wrap gap-3 text-[11px]">
            {segments.map((s) => (
              <span key={s.key} className="flex items-center gap-1.5">
                <span className={`inline-block w-2.5 h-2.5 rounded-sm ${s.color}`} />
                {s.label}: <strong>{s.count}</strong>
              </span>
            ))}
          </div>
        </>
      ) : (
        <p className="text-[11px] text-one-grey">Meg nincs lezart ugy draft-verzioval.</p>
      )}
    </div>
  );
}

function HandlingTimeCard({ handling }: { handling: OperationalMetrics["handling_time"] }) {
  return (
    <div className="bg-one-surface border border-one-line rounded-one shadow-card p-4">
      <h2 className="text-[13px] font-semibold mb-1">Ugykezelesi ido</h2>
      <p className="text-[11px] text-one-grey mb-3">
        Agent-feldolgozastol jovahagyasig eltelt ido ({handling.sample_size} minta).
      </p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-[12px]">
        <dt className="text-one-grey">Atlag</dt>
        <dd className="font-semibold">{formatDuration(handling.avg_seconds)}</dd>
        <dt className="text-one-grey">Median</dt>
        <dd className="font-semibold">{formatDuration(handling.median_seconds)}</dd>
      </dl>
    </div>
  );
}

function FeedbackByCategoryCard({ items }: { items: OperationalMetrics["feedback"]["by_category"] }) {
  return (
    <div className="bg-one-surface border border-one-line rounded-one shadow-card overflow-hidden">
      <div className="px-4 pt-4 pb-2">
        <h2 className="text-[13px] font-semibold">Visszajelzes kategoriankent</h2>
      </div>
      {items.length ? (
        <table className="w-full text-[11px]">
          <thead className="bg-one-canvas border-y border-one-line">
            <tr>
              <th className="text-left px-4 py-2 text-one-grey font-semibold">Kategoria</th>
              <th className="text-right px-4 py-2 text-one-grey font-semibold">Jo</th>
              <th className="text-right px-4 py-2 text-one-grey font-semibold">Rossz</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-one-line">
            {items.map((row) => (
              <tr key={row.category}>
                <td className="px-4 py-2">{row.category}</td>
                <td className="px-4 py-2 text-right text-kpi-ok font-semibold">{row.good}</td>
                <td className="px-4 py-2 text-right text-kpi-bad font-semibold">{row.bad}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="text-[11px] text-one-grey px-4 pb-4">Meg nincs ugyintezoi visszajelzes.</p>
      )}
    </div>
  );
}

function FeedbackReasonsCard({ byReason }: { byReason: Record<string, number> }) {
  const entries = Object.entries(byReason).sort(([, a], [, b]) => b - a);
  return (
    <div className="bg-one-surface border border-one-line rounded-one shadow-card p-4">
      <h2 className="text-[13px] font-semibold mb-1">Negativ visszajelzes okai</h2>
      <p className="text-[11px] text-one-grey mb-3">A rossz visszajelzesekhez valasztott okkodok megoszlasa.</p>
      {entries.length ? (
        <div className="flex flex-col gap-1.5">
          {entries.map(([code, count]) => (
            <div key={code} className="flex items-center justify-between text-[12px]">
              <span>{FEEDBACK_REASON_LABELS[code as keyof typeof FEEDBACK_REASON_LABELS] ?? code}</span>
              <span className="font-semibold">{count}</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-[11px] text-one-grey">Meg nincs okkoddal ellatott visszajelzes.</p>
      )}
    </div>
  );
}
