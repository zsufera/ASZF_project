import { AlertTriangle, CheckCircle2, FileSearch, ShieldAlert, Tag } from "lucide-react";
import type { Case } from "../../lib/types";

interface CaseDecisionSummaryProps {
  caseData: Case;
}

function pct(v: number | undefined) {
  if (v === undefined) return null;
  return `${Math.round(v * 100)}%`;
}

function confidenceColor(v: number | undefined) {
  if (v === undefined) return "text-one-grey";
  if (v >= 0.8) return "text-kpi-ok";
  if (v >= 0.6) return "text-kpi-warn";
  return "text-kpi-bad";
}

export function CaseDecisionSummary({ caseData }: CaseDecisionSummaryProps) {
  const state = caseData.agent_state;
  if (!state) return null;

  const classifyStep = state.timeline.find((s) => s.step === "classify");
  const priorityStep = state.timeline.find((s) => s.step === "priority_triage");
  const retrievalStep = state.timeline.find((s) => s.step === "retrieve");

  const category = (classifyStep?.output?.category as string | undefined) ?? caseData.category_label ?? "—";
  const subtype = classifyStep?.output?.subtype as string | undefined;
  const confidence = (classifyStep?.output?.confidence as number | undefined) ?? caseData.confidence;

  const priorityValue = (priorityStep?.output?.value as string | undefined) ??
    (caseData.priority === "surgos" ? "sürgős" : "normál");
  const priorityReason = priorityStep?.output?.reason as string | undefined;

  const chunkCount = state.retrieval?.chunks?.length ?? (retrievalStep?.output?.chunk_count as number | undefined) ?? 0;
  const generationMode = state.draft?.generation_mode;
  const coverageOk = generationMode !== "insufficient" && chunkCount > 0;

  const escalation = state.escalation;

  return (
    <div className="grid grid-cols-4 gap-3 mb-4 stagger-children">
      <SummaryCard
        icon={<Tag size={14} />}
        label="Kategória"
        value={category}
        sub={subtype}
        accentClass="border-l-one-turq"
      />
      <SummaryCard
        icon={<ShieldAlert size={14} />}
        label="Bizalom"
        value={pct(confidence) ?? "—"}
        valueClass={confidenceColor(confidence)}
        sub={confidence !== undefined && confidence < 0.6 ? "Alacsony megbízhatóság" : undefined}
        accentClass={confidence !== undefined && confidence >= 0.7 ? "border-l-kpi-ok" : "border-l-kpi-warn"}
      />
      <SummaryCard
        icon={<FileSearch size={14} />}
        label="ÁSZF-fedezet"
        value={coverageOk ? `${chunkCount} forrás` : "Hiányos"}
        valueClass={coverageOk ? "text-kpi-ok" : "text-kpi-bad"}
        sub={generationMode === "insufficient" ? "Emberi ellenőrzés javasolt" : undefined}
        accentClass={coverageOk ? "border-l-kpi-ok" : "border-l-kpi-bad"}
      />
      <SummaryCard
        icon={escalation?.required ? <AlertTriangle size={14} /> : <CheckCircle2 size={14} />}
        label="Státusz"
        value={escalation?.required ? "Eszkaláció" : priorityValue}
        valueClass={escalation?.required ? "text-status-esc-fg" : priorityValue === "sürgős" ? "text-status-urgent-fg" : "text-kpi-ok"}
        sub={escalation?.required ? (escalation.reasons[0] ?? undefined) : priorityReason}
        accentClass={escalation?.required ? "border-l-status-esc-fg" : "border-l-one-line"}
      />
    </div>
  );
}

function SummaryCard({
  icon,
  label,
  value,
  valueClass = "text-one-ink",
  sub,
  accentClass = "border-l-one-line",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  valueClass?: string;
  sub?: string;
  accentClass?: string;
}) {
  return (
    <div className={`bg-one-surface border border-one-line border-l-4 ${accentClass} rounded-one px-3 py-2.5`}>
      <div className="flex items-center gap-1.5 text-one-grey mb-1">
        {icon}
        <span className="text-[10px] uppercase tracking-wider font-semibold">{label}</span>
      </div>
      <div className={`text-[14px] font-bold leading-tight ${valueClass}`}>{value}</div>
      {sub && <div className="text-[10px] text-one-grey mt-0.5 line-clamp-1">{sub}</div>}
    </div>
  );
}
