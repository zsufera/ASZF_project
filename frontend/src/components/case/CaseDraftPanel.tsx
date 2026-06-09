import type { MutableRefObject } from "react";
import type { Case, EscalationState, OutputMode, SourceRef } from "../../lib/types";
import { Card } from "../Card";
import { DraftEditor } from "../DraftEditor";
import { InlineAnswer } from "../InlineAnswer";
import { ProcessingIndicator } from "../ProcessingIndicator";

interface CaseDraftPanelProps {
  caseData: Case;
  draft: Case["agent_state"]["draft"];
  sources: SourceRef[];
  hasTimeline: boolean;
  escalation: EscalationState | null;
  generationMode?: string;
  processing: boolean;
  outputMode: OutputMode;
  sourceRefs: MutableRefObject<Record<string, HTMLDivElement | null>>;
  onProcess: () => void;
  onModeChange: (mode: OutputMode) => void;
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
  generationMode,
  processing,
  outputMode,
  sourceRefs,
  onProcess,
  onModeChange,
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
            aria-label="Agent feldolgozas ujrafuttatasa"
          >
            {processing ? "Feldolgozas..." : "Feldolgozas ujra"}
          </button>
        </div>
      ) : null}

      {escalation?.required ? (
        <div className="mb-3 bg-status-esc-bg border border-status-esc-fg rounded-md p-2 text-[11px] text-status-esc-fg">
          Eszkalacio supervisorhoz szukseges: {escalation.reasons.join(", ")}
        </div>
      ) : null}

      {generationMode === "insufficient" && !processing ? (
        <div className="mb-3 bg-status-esc-bg border border-status-esc-fg rounded-md p-2 text-[11px] text-status-esc-fg">
          Nincs eleg ASZF-fedezet automatikus valaszhoz; emberi ellenorzes javasolt.
        </div>
      ) : null}

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
            Agent feldolgozas inditasa
          </button>
        </div>
      ) : (
        <>
          {draft.body_masked ? (
            <div className="mb-3 bg-[#FbFdfd] border border-one-line rounded-md p-2">
              <div className="text-[9px] uppercase text-one-grey tracking-wider mb-1">
                Fedezet-elonezet
              </div>
              <InlineAnswer
                body={draft.body_masked}
                sources={sources}
                onCite={(ref) => {
                  const el = sourceRefs.current[ref];
                  if (!el) return;
                  el.scrollIntoView({ behavior: "smooth", block: "center" });
                  el.classList.add("ring-2", "ring-one-turq");
                  setTimeout(() => el.classList.remove("ring-2", "ring-one-turq"), 1500);
                }}
              />
            </div>
          ) : null}
          <DraftEditor
            draft={draft}
            versions={caseData.draft_versions}
            outputMode={outputMode}
            caseId={caseData.case_id}
            onModeChange={onModeChange}
            onSave={onSave}
            onApprove={onApprove}
            onFeedback={onFeedback}
            onCitationClick={onCitationClick}
          />
        </>
      )}
    </Card>
  );
}
