import { useState } from "react";
import type { MutableRefObject } from "react";
import { AlertTriangle, CheckCircle2, ChevronDown, ShieldCheck, XCircle } from "lucide-react";
import type { Case, EscalationState, FeedbackReason, SourceRef, TimelineStep, VerifyState } from "../../lib/types";
import { Card } from "../Card";
import { DraftEditor } from "../DraftEditor";
import { ProcessingIndicator } from "../ProcessingIndicator";
import { reasonLabel } from "../../lib/agentSteps";

interface CaseDraftPanelProps {
  caseData: Case;
  draft: Case["agent_state"]["draft"];
  sources: SourceRef[];
  hasTimeline: boolean;
  escalation: EscalationState | null;
  verify?: VerifyState;
  missingMandatory?: string[];
  generationMode?: string;
  processing: boolean;
  processingSteps?: TimelineStep[];
  sourceRefs: MutableRefObject<Record<string, HTMLDivElement | null>>;
  onProcess: () => void;
  onSave: (subject: string, body: string) => Promise<void>;
  onApprove: (subject: string, body: string, versionId: string) => Promise<void>;
  onFeedback: (rating: "jo" | "rossz", reason?: FeedbackReason) => Promise<void>;
  onCitationClick: (citation: string) => void;
}

export function CaseDraftPanel({
  caseData,
  draft,
  hasTimeline,
  escalation,
  verify,
  missingMandatory = [],
  generationMode,
  processing,
  processingSteps = [],
  onProcess,
  onSave,
  onApprove,
  onFeedback,
  onCitationClick,
}: CaseDraftPanelProps) {
  return (
    <Card title="Draft">
      {hasTimeline && !processing ? (
        <DraftChecklist
          escalation={escalation}
          verify={verify}
          missingMandatory={missingMandatory}
          generationMode={generationMode}
          onCitationClick={onCitationClick}
        />
      ) : null}

      {processing ? (
        <ProcessingIndicator active={processing} steps={processingSteps} />
      ) : !hasTimeline ? (
        <div className="text-center py-6">
          <p className="text-one-grey text-[12px] mb-3">Az agent még nem futott.</p>
          <button
            onClick={onProcess}
            disabled={processing}
            className="bg-one-turq text-[#04201f] font-bold text-[12px] px-5 py-2 rounded-pill hover:bg-one-turq-d transition-colors disabled:opacity-50 btn-press"
          >
            Agent feldolgozás indítása
          </button>
        </div>
      ) : (
        <DraftEditor
          draft={draft}
          versions={caseData.draft_versions}
          caseId={caseData.case_id}
          onSave={onSave}
          onApprove={onApprove}
          onFeedback={onFeedback}
          onCitationClick={onCitationClick}
        />
      )}
    </Card>
  );
}

/* ============================================================
   Ellenőrzés — összevont draft minőségi checklist
   ============================================================ */

type CheckStatus = "ok" | "warn" | "error" | "neutral";

function StatusIcon({ status }: { status: CheckStatus }) {
  if (status === "error") return <XCircle size={14} className="text-status-urgent-fg shrink-0" aria-label="Hiba" />;
  if (status === "warn") return <AlertTriangle size={14} className="text-status-esc-fg shrink-0" aria-label="Figyelmeztetés" />;
  if (status === "ok") return <CheckCircle2 size={14} className="text-kpi-ok shrink-0" aria-label="Rendben" />;
  return <CheckCircle2 size={14} className="text-one-grey shrink-0" aria-label="Nincs adat" />;
}

function ChecklistRow({
  status,
  label,
  summary,
  children,
}: {
  status: CheckStatus;
  label: string;
  summary: string;
  children?: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const hasDetail = Boolean(children);
  const summaryTone = status === "error" ? "text-status-urgent-fg" : status === "warn" ? "text-status-esc-fg" : "text-one-grey";

  return (
    <div className="px-3 py-2">
      <button
        type="button"
        onClick={() => hasDetail && setOpen((o) => !o)}
        className={`flex items-center gap-2 w-full text-left text-[11px] ${hasDetail ? "cursor-pointer" : "cursor-default"} focus-visible:ring-2 focus-visible:ring-one-turq rounded`}
        aria-expanded={hasDetail ? open : undefined}
        disabled={!hasDetail}
      >
        <StatusIcon status={status} />
        <span className="font-semibold text-one-ink">{label}</span>
        <span className={`truncate ${summaryTone}`}>{summary}</span>
        {hasDetail ? (
          <ChevronDown size={13} className={`ml-auto shrink-0 text-one-grey transition-transform ${open ? "rotate-180" : ""}`} />
        ) : null}
      </button>
      {open && hasDetail ? <div className="mt-2 ml-6 animate-fade-in">{children}</div> : null}
    </div>
  );
}

function DraftChecklist({
  escalation,
  verify,
  missingMandatory = [],
  generationMode,
  onCitationClick,
}: {
  escalation: EscalationState | null;
  verify?: VerifyState;
  missingMandatory?: string[];
  generationMode?: string;
  onCitationClick: (citation: string) => void;
}) {
  const escalationRequired = Boolean(escalation?.required);
  const coverageInsufficient = generationMode === "insufficient";
  const claims = verify?.claims ?? [];
  const ungrounded = claims.filter((c) => !c.grounded);
  const groundingProblem = ungrounded.length > 0;
  const mandatoryMissing = missingMandatory.length > 0;

  const problems = [escalationRequired, coverageInsufficient, groundingProblem, mandatoryMissing].filter(Boolean).length;

  return (
    <div className="mb-3 rounded-md border border-one-line bg-one-surface overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-one-line bg-one-canvas">
        <span className="text-[10px] uppercase tracking-wider text-one-grey font-semibold flex items-center gap-1.5">
          <ShieldCheck size={12} /> Ellenőrzés
        </span>
        <span className={`text-[10px] font-semibold ${problems ? "text-status-esc-fg" : "text-kpi-ok"}`}>
          {problems ? `${problems} figyelmeztetés` : "Minden rendben"}
        </span>
      </div>
      <div className="divide-y divide-one-line">
        <ChecklistRow
          status={escalationRequired ? "warn" : "ok"}
          label="Eszkaláció"
          summary={escalationRequired ? "Supervisor felülvizsgálat szükséges" : "Nem szükséges"}
        >
          {escalationRequired ? (
            <div className="flex flex-wrap gap-1">
              {escalation!.reasons.map((reason) => (
                <span key={reason} className="rounded-full bg-status-esc-bg text-status-esc-fg px-2 py-0.5 text-[10px]">
                  {reasonLabel(reason)}
                </span>
              ))}
            </div>
          ) : null}
        </ChecklistRow>

        <ChecklistRow
          status={coverageInsufficient ? "error" : "ok"}
          label="ÁSZF-fedezet"
          summary={coverageInsufficient ? "Nincs elég fedezet — emberi ellenőrzés javasolt" : "Megfelelő forrásfedezet"}
        />

        <GroundingClaimsPanel verify={verify} onCitationClick={onCitationClick} />
        <MandatoryReferencesPanel missing={missingMandatory} />
      </div>
    </div>
  );
}

export function GroundingClaimsPanel({
  verify,
  onCitationClick,
}: {
  verify?: VerifyState;
  onCitationClick: (citation: string) => void;
}) {
  const claims = verify?.claims ?? [];
  const ungrounded = claims.filter((claim) => !claim.grounded);
  const status: CheckStatus = !claims.length ? "neutral" : ungrounded.length ? "warn" : "ok";
  const summary = !claims.length
    ? "Nincs ellenőrzött állítás"
    : ungrounded.length
      ? `${ungrounded.length} nem megalapozott állítás`
      : "Minden állítás fedett";

  return (
    <ChecklistRow status={status} label="Grounding ellenőrzés" summary={summary}>
      {claims.length ? (
        <div className="space-y-1">
          {claims.slice(0, 6).map((claim, idx) => (
            <div key={`${claim.chunk_id ?? "claim"}-${idx}`} className="flex items-start gap-2 text-[11px]">
              <span className={claim.grounded ? "text-kpi-ok" : "text-status-esc-fg"} aria-hidden="true">
                {claim.grounded ? "✓" : "!"}
              </span>
              <button
                type="button"
                onClick={() => claim.chunk_id && onCitationClick(claim.chunk_id)}
                className="text-left text-one-grey hover:text-one-turq-d disabled:hover:text-one-grey"
                disabled={!claim.chunk_id}
              >
                {claim.claim}
              </button>
            </div>
          ))}
        </div>
      ) : null}
    </ChecklistRow>
  );
}

export function MandatoryReferencesPanel({ missing }: { missing: string[] }) {
  const status: CheckStatus = missing.length ? "error" : "ok";
  const summary = missing.length ? `${missing.length} hiányzó hivatkozás` : "Minden kötelező hivatkozás megvan";

  return (
    <ChecklistRow status={status} label="Kötelező hivatkozások" summary={summary}>
      {missing.length ? (
        <div className="flex flex-wrap gap-1">
          {missing.map((item) => (
            <span key={item} className="rounded-full bg-status-esc-bg text-status-esc-fg px-2 py-0.5 text-[10px]">
              {item}
            </span>
          ))}
        </div>
      ) : null}
    </ChecklistRow>
  );
}
