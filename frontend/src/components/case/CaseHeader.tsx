import { ArrowLeft, RefreshCw } from "lucide-react";
import type { Case } from "../../lib/types";
import { Badge } from "../Badge";

interface CaseHeaderProps {
  caseData: Case;
  onBack: () => void;
  onProcess?: () => void;
  processing?: boolean;
  canReprocess?: boolean;
}

export function CaseHeader({ caseData, onBack, onProcess, processing = false, canReprocess = false }: CaseHeaderProps) {
  return (
    <>
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-one-turq-d font-semibold text-[12px] hover:underline mb-3"
        aria-label="Vissza a bejövő ügyekhez"
      >
        <ArrowLeft size={14} />
        Vissza a bejövő ügyekhez
      </button>

      <div className="bg-gradient-to-r from-one-turq-l to-white border border-one-line rounded-one p-3 mb-4">
        <div className="flex flex-wrap items-center gap-3 mb-2">
          <div className="min-w-0">
            <h1 className="text-[16px] font-bold text-one-ink leading-snug">{caseData.category_label}</h1>
            <code className="font-mono text-[11px] text-one-grey">#{caseData.case_id}</code>
          </div>
          {canReprocess && onProcess ? (
            <button
              onClick={onProcess}
              disabled={processing}
              className="inline-flex items-center gap-1.5 bg-one-turq text-[#04201f] font-bold text-[12px] px-4 py-2 rounded-pill shadow-card hover:bg-one-turq-d transition-colors disabled:opacity-50 btn-press"
              aria-label="Agent feldolgozás újrafuttatása"
            >
              <RefreshCw size={14} className={processing ? "animate-spin" : undefined} />
              {processing ? "Feldolgozás…" : "Feldolgozás újra"}
            </button>
          ) : null}
          <div className="flex items-center gap-2 flex-wrap shrink-0 ml-auto">
            {caseData.priority === "surgos" ? <Badge kind="priority" value="SÜRGŐS" /> : null}
            {caseData.escalated ? <Badge kind="escalation" value="Eszkalált" /> : null}
            {caseData.confidence < 0.7 ? <Badge kind="confidence" value={caseData.confidence} /> : null}
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap text-[11px] text-one-grey">
          <span className="bg-white border border-one-line rounded px-1.5 py-0.5 text-[10px]">
            {caseData.channel_label}
          </span>
          <span>Email: {caseData.sender_email_display}</span>
          <span className="ml-auto bg-white border border-one-line rounded-lg px-2 py-0.5 font-semibold text-one-ink">
            SLA: {caseData.sla_days_remaining} nap
          </span>
        </div>
      </div>
    </>
  );
}
