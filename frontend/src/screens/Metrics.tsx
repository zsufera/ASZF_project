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
      setError(e instanceof Error ? e.message : "Nem sikerült betölteni a méréseket");
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
          <h1 className="text-[16px] font-bold text-one-ink">Visszamérés</h1>
          <button
            onClick={load}
            disabled={loading}
            className="text-[11px] border border-one-line px-3 py-1 rounded-pill hover:bg-one-canvas transition-colors disabled:opacity-50"
          >
            Frissítés
          </button>
        </div>
        {error ? (
          <div className="text-status-urgent-fg text-[12px]" role="alert">{error}</div>
        ) : (
          <div className="text-[12px] text-one-grey">{loading ? "Betöltés..." : "Nincs megjeleníthető adat."}</div>
        )}
      </div>
    );
  }

  const { case_funnel, handling_time, draft_acceptance, feedback, escalation } = metrics;
  const kpiItems = [
    {
      label: "Copilot-lefedettség",
      value: pct(case_funnel.adoption_rate),
      status: (case_funnel.adoption_rate >= 0.7 ? "green" : case_funnel.adoption_rate >= 0.4 ? "yellow" : "red") as KpiStatus,
    },
    {
      label: "Átlagos átfutási idő",
      value: formatDuration(handling_time.avg_seconds),
      status: (handling_time.avg_seconds === null || handling_time.avg_seconds <= 300 ? "green" : "yellow") as KpiStatus,
    },
    {
      label: "Pozitív visszajelzés",
      value: pct(feedback.positive_rate),
      status: (feedback.positive_rate === null || feedback.positive_rate >= 0.75 ? "green" : feedback.positive_rate >= 0.5 ? "yellow" : "red") as KpiStatus,
    },
    {
      label: "Eszkalációs arány",
      value: pct(escalation.escalation_rate),
      status: (escalation.escalation_rate > 0.1 ? "yellow" : "green") as KpiStatus,
    },
    {
      label: "Lezárt ügyek",
      value: case_funnel.closed_cases,
      status: "green" as KpiStatus,
    },
    {
      label: "Draft minták",
      value: draft_acceptance.sample_size,
      status: "green" as KpiStatus,
    },
    {
      label: "Rossz forrás jelzés",
      value: feedback.wrong_source,
      status: (feedback.wrong_source > 3 ? "yellow" : "green") as KpiStatus,
    },
    {
      label: "Összes ügy",
      value: case_funnel.total_cases,
      status: "green" as KpiStatus,
    },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-[16px] font-bold text-one-ink">Visszamérés</h1>
        <button
          onClick={load}
          disabled={loading}
          className="text-[11px] border border-one-line px-3 py-1 rounded-pill hover:bg-one-canvas transition-colors disabled:opacity-50"
        >
          {loading ? "Frissítés..." : "Frissítés"}
        </button>
      </div>
      <p className="text-[12px] text-one-grey mb-4">
        Élő működési mutatók a feldolgozott ügyek audit-naplójából.
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
    { key: "unchanged", label: "Változtatás nélkül", count: acceptance.unchanged, color: "bg-kpi-ok" },
    { key: "light_edit", label: "Kis szerkesztés", count: acceptance.light_edit, color: "bg-kpi-warn" },
    { key: "rewrite", label: "Újraírás", count: acceptance.rewrite, color: "bg-kpi-bad" },
  ];
  return (
    <div className="bg-one-surface border border-one-line rounded-one shadow-card p-4">
      <h2 className="text-[13px] font-semibold mb-1">Draft-átvétel megoszlása</h2>
      <p className="text-[11px] text-one-grey mb-3">
        Első draft és végleges szöveg eltérése ({total} lezárt ügy).
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
        <p className="text-[11px] text-one-grey">Még nincs lezárt ügy draft-verzióval.</p>
      )}
    </div>
  );
}

function HandlingTimeCard({ handling }: { handling: OperationalMetrics["handling_time"] }) {
  return (
    <div className="bg-one-surface border border-one-line rounded-one shadow-card p-4">
      <h2 className="text-[13px] font-semibold mb-1">Ügykezelési idő</h2>
      <p className="text-[11px] text-one-grey mb-3">
        Agent-feldolgozástól jóváhagyásig eltelt idő ({handling.sample_size} minta).
      </p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-[12px]">
        <dt className="text-one-grey">Átlag</dt>
        <dd className="font-semibold">{formatDuration(handling.avg_seconds)}</dd>
        <dt className="text-one-grey">Medián</dt>
        <dd className="font-semibold">{formatDuration(handling.median_seconds)}</dd>
      </dl>
    </div>
  );
}

function FeedbackByCategoryCard({ items }: { items: OperationalMetrics["feedback"]["by_category"] }) {
  return (
    <div className="bg-one-surface border border-one-line rounded-one shadow-card overflow-hidden">
      <div className="px-4 pt-4 pb-2">
        <h2 className="text-[13px] font-semibold">Visszajelzés kategóriánként</h2>
      </div>
      {items.length ? (
        <table className="w-full text-[11px]">
          <thead className="bg-one-canvas border-y border-one-line">
            <tr>
              <th className="text-left px-4 py-2 text-one-grey font-semibold">Kategória</th>
              <th className="text-right px-4 py-2 text-one-grey font-semibold">Jó</th>
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
        <p className="text-[11px] text-one-grey px-4 pb-4">Még nincs ügyintézői visszajelzés.</p>
      )}
    </div>
  );
}

function FeedbackReasonsCard({ byReason }: { byReason: Record<string, number> }) {
  const entries = Object.entries(byReason).sort(([, a], [, b]) => b - a);
  return (
    <div className="bg-one-surface border border-one-line rounded-one shadow-card p-4">
      <h2 className="text-[13px] font-semibold mb-1">Negatív visszajelzés okai</h2>
      <p className="text-[11px] text-one-grey mb-3">A rossz visszajelzésekhez választott okkódok megoszlása.</p>
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
        <p className="text-[11px] text-one-grey">Még nincs okkóddal ellátott visszajelzés.</p>
      )}
    </div>
  );
}
