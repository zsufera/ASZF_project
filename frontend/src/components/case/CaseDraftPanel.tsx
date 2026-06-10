import type { MutableRefObject } from "react";
import type { Case, EscalationState, SourceRef, VerifyState } from "../../lib/types";
import { Card } from "../Card";
import { DraftEditor } from "../DraftEditor";
import { ProcessingIndicator } from "../ProcessingIndicator";

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
  sourceRefs: MutableRefObject<Record<string, HTMLDivElement | null>>;
  onProcess: () => void;
  onSave: (subject: string, body: string) => Promise<void>;
  onApprove: (subject: string, body: string, versionId: string) => Promise<void>;
  onFeedback: (rating: "jo" | "rossz", wrongSource?: boolean) => Promise<void>;
  onCitationClick: (citation: string) => void;
}

export function CaseDraftPanel({
  caseData,
  draft,
  sources,
  hasTimeline,
  escalation,
  verify,
  missingMandatory = [],
  generationMode,
  processing,
  sourceRefs,
  onProcess,
  onSave,
  onApprove,
  onFeedback,
  onCitationClick,
}: CaseDraftPanelProps) {
  return (
    <Card title="Draft">
      {hasTimeline ? (
        <div className="flex justify-end mb-2">
          <button
            onClick={onProcess}
            disabled={processing}
            className="text-[10px] text-one-turq-d border border-one-turq rounded-pill px-3 py-1 hover:bg-one-turq-l transition-colors disabled:opacity-50"
            aria-label="Agent feldolgozás újrafuttatása"
          >
            {processing ? "Feldolgozás…" : "Feldolgozás újra"}
          </button>
        </div>
      ) : null}

      {escalation?.required ? (
        <div className="mb-3 bg-status-esc-bg border border-status-esc-fg rounded-md p-2 text-[11px] text-status-esc-fg">
          Eszkaláció supervisorhoz szükséges: {escalation.reasons.join(", ")}
        </div>
      ) : null}

      {generationMode === "insufficient" && !processing ? (
        <div className="mb-3 bg-status-esc-bg border border-status-esc-fg rounded-md p-2 text-[11px] text-status-esc-fg">
          Nincs elég ÁSZF-fedezet automatikus válaszhoz; emberi ellenőrzés javasolt.
        </div>
      ) : null}

      <GroundingClaimsPanel verify={verify} onCitationClick={onCitationClick} />
      <MandatoryReferencesPanel missing={missingMandatory} />

      {processing ? (
        <ProcessingIndicator active={processing} />
      ) : !hasTimeline ? (
        <div className="text-center py-6">
          <p className="text-one-grey text-[12px] mb-3">Az agent meg nem futott.</p>
          <button
            onClick={onProcess}
            disabled={processing}
            className="bg-one-turq text-[#04201f] font-bold text-[12px] px-5 py-2 rounded-pill hover:bg-one-turq-d transition-colors disabled:opacity-50"
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

export function GroundingClaimsPanel({
  verify,
  onCitationClick,
}: {
  verify?: VerifyState;
  onCitationClick: (citation: string) => void;
}) {
  const claims = verify?.claims ?? [];
  if (!claims.length) return null;

  const ungrounded = claims.filter((claim) => !claim.grounded);
  return (
    <div className="mb-3 rounded-md border border-one-line bg-one-canvas p-2 text-[11px]">
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="font-semibold text-one-ink">Grounding ellenőrzés</span>
        <span className={ungrounded.length ? "text-status-esc-fg" : "text-kpi-ok"}>
          {ungrounded.length ? `${ungrounded.length} nem megalapozott` : "minden állítás fedett"}
        </span>
      </div>
      <div className="space-y-1">
        {claims.slice(0, 6).map((claim, idx) => (
          <div key={`${claim.chunk_id ?? "claim"}-${idx}`} className="flex items-start gap-2">
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
    </div>
  );
}

export function MandatoryReferencesPanel({ missing }: { missing: string[] }) {
  if (!missing.length) return null;
  return (
    <div className="mb-3 rounded-md border border-status-esc-fg bg-status-esc-bg p-2 text-[11px] text-status-esc-fg">
      <div className="font-semibold mb-1">Hiányzó kötelező hivatkozások</div>
      <div className="flex flex-wrap gap-1">
        {missing.map((item) => (
          <span key={item} className="rounded-full bg-white/70 px-2 py-0.5 text-[10px]">{item}</span>
        ))}
      </div>
    </div>
  );
}
