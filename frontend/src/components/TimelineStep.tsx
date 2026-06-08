import { useState } from "react";
import type { TimelineStep as TStep } from "../lib/types";

const STEP_LABELS: Record<string, string> = {
  language: "Nyelv / típus",
  mask: "Maszkolás",
  classify: "Osztályozás",
  priority: "Prioritás",
  policy_map: "Szabályzat-térkép",
  escalation: "Eszkaláció",
  draft: "Draft",
  verify: "Ellenőrzés",
};

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
  const label = STEP_LABELS[step.step] ?? step.step;

  const summary = (() => {
    const out = step.output as Record<string, unknown>;
    if (step.step === "language") return `${out.language ?? "—"} · ${out.type ?? "—"}`;
    if (step.step === "mask") return `${out.pii_count ?? 0} PII token`;
    if (step.step === "classify") return `${out.category ?? "—"} · ${out.confidence ?? "—"}`;
    if (step.step === "priority") return String(out.priority ?? "—");
    if (step.step === "escalation") return out.required ? `ok: ${(out.reasons as string[])?.join(", ")}` : "nem szükséges";
    if (step.step === "verify") return `${out.ungrounded_count ?? 0} nem megalapozott`;
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
        <pre className="mt-1 ml-6 text-[9px] bg-one-canvas border border-one-line rounded p-2 overflow-auto max-h-40 whitespace-pre-wrap break-all animate-fade-in">
          {JSON.stringify(step.output, null, 2)}
        </pre>
      )}
    </div>
  );
}
