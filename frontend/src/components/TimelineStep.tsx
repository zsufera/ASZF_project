import { useState } from "react";
import { AlertTriangle, Check, ChevronDown, Loader2, X } from "lucide-react";
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
  const base = "w-[18px] h-[18px] rounded-full flex items-center justify-center flex-none";
  if (status === "ok") return <span className={`${base} bg-one-turq text-[#04201f]`} aria-label="Kész"><Check size={11} strokeWidth={3} /></span>;
  if (status === "warn") return <span className={`${base} bg-[#f5a623] text-[#3a2400]`} aria-label="Figyelmeztetés"><AlertTriangle size={11} strokeWidth={2.5} /></span>;
  if (status === "run") return <span className={`${base} bg-one-turq-l text-one-turq-d`} aria-label="Fut"><Loader2 size={11} className="animate-spin" /></span>;
  return <span className={`${base} bg-status-urgent-bg text-status-urgent-fg`} aria-label="Hiba"><X size={11} strokeWidth={3} /></span>;
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
        className="flex gap-2 items-start w-full text-left focus-visible:ring-2 focus-visible:ring-one-turq rounded group"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={`${label} lépés részletei`}
      >
        <DotIcon status={status} />
        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-semibold">{label}</div>
          {summary && <div className="text-[10px] text-one-grey truncate">{summary}</div>}
        </div>
        <ChevronDown size={13} className={`shrink-0 mt-0.5 text-one-line group-hover:text-one-grey transition-transform ${open ? "rotate-180" : ""}`} />
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
