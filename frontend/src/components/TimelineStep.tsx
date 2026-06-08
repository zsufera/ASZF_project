import { useState } from "react";
import type { TimelineStep as TStep } from "../lib/types";
import { STEP_META, stepLabel, fieldLabel, formatFieldValue } from "../lib/agentSteps";

function stepStatus(step: TStep): "ok" | "warn" | "run" | "error" {
  const out = step.output as Record<string, unknown>;
  if (out?.error) return "error";
  if (out?.required === true || out?.ungrounded_count) return "warn";
  if (out?.running) return "run";
  return "ok";
}

function DotIcon({ status }: { status: "ok" | "warn" | "run" | "error" }) {
  if (status === "ok") return <span className="w-[18px] h-[18px] rounded-full bg-one-turq text-[#04201f] text-[10px] flex items-center justify-center font-bold flex-none" aria-label="Kész">✓</span>;
  if (status === "warn") return <span className="w-[18px] h-[18px] rounded-full bg-[#f5a623] text-[#3a2400] text-[10px] flex items-center justify-center font-bold flex-none" aria-label="Figyelmeztetés">!</span>;
  if (status === "run") return <span className="w-[18px] h-[18px] rounded-full bg-one-turq-l text-one-turq-d text-[10px] flex items-center justify-center flex-none animate-spin" aria-label="Fut">⟳</span>;
  return <span className="w-[18px] h-[18px] rounded-full bg-status-urgent-bg text-status-urgent-fg text-[10px] flex items-center justify-center font-bold flex-none" aria-label="Hiba">✗</span>;
}

export function TimelineStepItem({ step }: { step: TStep }) {
  const [open, setOpen] = useState(false);
  const status = stepStatus(step);
  const label = stepLabel(step.step);

  const out = step.output as Record<string, unknown>;
  const meta = STEP_META[step.step];

  const summary = (() => {
    if (step.step === "classify") return `${formatFieldValue("category", out.category)} · ${formatFieldValue("confidence", out.confidence)}`;
    if (step.step === "escalation") return out.required ? `ok: ${formatFieldValue("reasons", out.reasons)}` : "nem szükséges";
    if (step.step === "retrieve") return `${formatFieldValue("result_count", out.result_count)} találat`;
    if (step.step === "draft") return `${formatFieldValue("generation_mode", out.generation_mode)} · ${formatFieldValue("source_count", out.source_count)} forrás`;
    if (step.step === "verify") return `${formatFieldValue("ungrounded_count", out.ungrounded_count)} nem megalapozott`;
    if (step.step === "priority_triage") return formatFieldValue("value", out.value);
    if (meta && meta.fields.length) { const k = meta.fields[0]; return `${fieldLabel(k)}: ${formatFieldValue(k, out[k])}`; }
    return "";
  })();

  return (
    <div className="py-1.5">
      <button
        className="flex gap-2 items-start w-full text-left focus-visible:ring-2 focus-visible:ring-one-turq rounded"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={`${label} lépés részletei`}
      >
        <DotIcon status={status} />
        <div>
          <div className="text-[11px] font-semibold">{label}</div>
          {summary && <div className="text-[10px] text-one-grey">{summary}</div>}
        </div>
      </button>
      {open && (
        <div className="mt-1 ml-6 text-[10px] bg-one-canvas border border-one-line rounded p-2 animate-fade-in">
          {meta?.explain && <p className="text-one-grey mb-2">{meta.explain}</p>}
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
            {(meta ? meta.fields.filter((k) => out[k] !== undefined) : Object.keys(out)).map((k) => (
              <div key={k} className="contents">
                <dt className="text-one-grey">{fieldLabel(k)}</dt>
                <dd className="text-one-ink font-medium break-words">{formatFieldValue(k, out[k])}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </div>
  );
}
