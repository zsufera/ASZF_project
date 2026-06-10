import { useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { CaseCustomerPanel } from "../components/case/CaseCustomerPanel";
import { CaseDraftPanel } from "../components/case/CaseDraftPanel";
import { CaseDecisionSummary } from "../components/case/CaseDecisionSummary";
import { CaseHeader } from "../components/case/CaseHeader";
import { CaseHistoryPanel } from "../components/case/CaseHistoryPanel";
import { CaseInboundMessage } from "../components/case/CaseInboundMessage";
import { CaseSourcesPanel } from "../components/case/CaseSourcesPanel";
import { CaseTimelinePanel } from "../components/case/CaseTimelinePanel";
import { AuditPanel } from "../components/case/AuditPanel";
import { Modal } from "../components/Modal";
import { useCaseActions } from "../hooks/useCaseActions";
import { useCaseData } from "../hooks/useCaseData";
import { useSession } from "../state/session";
import { useToast } from "../state/toast";

export function CaseWorkstation() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user, outputMode } = useSession();
  const { show } = useToast();
  const { caseData, history, loading, error, refetch } = useCaseData(id);

  const [selectedCustomer, setSelectedCustomer] = useState<string | null>(null);
  const [approvalResult, setApprovalResult] = useState<{ subject_unmasked: string; body_unmasked: string } | null>(null);
  const sourceRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const { processing, handleProcess, handleSave, handleApprove, handleFeedback } = useCaseActions({
    caseData,
    user,
    outputMode,
    onRefresh: refetch,
    onApproved: setApprovalResult,
    show,
  });

  if (loading) return <div className="text-one-grey p-8 text-center">Betöltés...</div>;
  if (error) return <div className="text-status-urgent-fg p-8">{error}</div>;
  if (!caseData) return null;

  const draft = caseData.agent_state?.draft ?? { subject: "", body_masked: "", citations: [] };
  const hasTimeline = (caseData.agent_state?.timeline ?? []).length > 0;
  const escalation = caseData.agent_state?.escalation ?? null;
  const chunks = caseData.agent_state?.retrieval?.chunks ?? [];
  const sources = caseData.agent_state?.draft?.sources ?? [];
  const generationMode = caseData.agent_state?.draft?.generation_mode;
  // Fix 3 oszlop: az agent-folyamat összecsukása ne tolja át a layoutot — a sáv a helyén marad.
  const cols = "grid-cols-case-open";

  const scrollToSourceKey = (key: string) => {
    const el = sourceRefs.current[key];
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.classList.add("ring-2", "ring-one-turq");
    setTimeout(() => el.classList.remove("ring-2", "ring-one-turq"), 1500);
  };

  const handleCitationClick = (citation: string) => {
    const richSource = sources.find((source) => source.chunk_id === citation || source.ref === citation);
    if (richSource) {
      scrollToSourceKey(richSource.ref);
      return;
    }

    const chunk = chunks.find((item) => item.paragrafus.includes(citation) || citation.includes(item.paragrafus));
    if (chunk) scrollToSourceKey(chunk.chunk_id);
  };

  return (
    <div>
      <CaseHeader
        caseData={caseData}
        onBack={() => navigate("/inbox")}
        onProcess={handleProcess}
        processing={processing}
        canReprocess={hasTimeline}
      />
      <CaseDecisionSummary caseData={caseData} />

      <div className={`grid gap-3 transition-all duration-200 ${cols}`}>
        <div className="flex flex-col gap-3 min-w-0">
          <CaseSourcesPanel
            sources={sources}
            chunks={chunks}
            unresolvedRefs={caseData.agent_state?.retrieval?.unresolved_refs ?? []}
            sourceRefs={sourceRefs}
          />
          <CaseCustomerPanel
            candidates={caseData.customer_candidates}
            selected={selectedCustomer}
            onSelect={setSelectedCustomer}
          />
          <CaseHistoryPanel items={history?.items ?? []} isRepeated={history?.is_repeated ?? false} />
          <div className="mt-1 pt-2 border-t border-one-line flex justify-end">
            <AuditPanel caseId={caseData.case_id} role={user?.role ?? "ui"} />
          </div>
        </div>

        <div className="flex flex-col gap-3 min-w-0">
          <CaseInboundMessage body={caseData.inbound_text_masked} />
          <CaseDraftPanel
            caseData={caseData}
            draft={draft}
            sources={sources}
            hasTimeline={hasTimeline}
            escalation={escalation}
            verify={caseData.agent_state?.verify}
            missingMandatory={caseData.agent_state?.policy_map?.missing_mandatory ?? []}
            generationMode={generationMode}
            processing={processing}
            sourceRefs={sourceRefs}
            onProcess={handleProcess}
            onSave={handleSave}
            onApprove={handleApprove}
            onFeedback={handleFeedback}
            onCitationClick={handleCitationClick}
          />
        </div>

        <CaseTimelinePanel
          hasTimeline={hasTimeline}
          steps={caseData.agent_state?.timeline ?? []}
          escalation={escalation}
        />
      </div>

      {approvalResult ? (
        <Modal title="Jóváhagyott tartalom — Küldésre kész" onClose={() => setApprovalResult(null)}>
          <div className="text-[12px] space-y-3">
            <div>
              <label className="text-one-grey text-[10px] uppercase">Tárgy</label>
              <p className="font-semibold mt-0.5">{approvalResult.subject_unmasked}</p>
            </div>
            <div>
              <label className="text-one-grey text-[10px] uppercase">Üzenet</label>
              <pre className="mt-0.5 whitespace-pre-wrap text-[11px] bg-one-canvas border border-one-line rounded p-2">
                {approvalResult.body_unmasked}
              </pre>
            </div>
            <button
              onClick={() => {
                show("Levél kiküldve!");
                setApprovalResult(null);
              }}
              className="bg-one-turq text-[#04201f] font-bold text-[11px] px-4 py-2 rounded-pill hover:bg-one-turq-d transition-colors w-full"
            >
              Küldés megerősítése
            </button>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
