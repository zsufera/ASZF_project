import { ArrowLeft } from "lucide-react";
import type { Case } from "../../lib/types";
import { Badge } from "../Badge";

interface CaseHeaderProps {
  caseData: Case;
  onBack: () => void;
}

export function CaseHeader({ caseData, onBack }: CaseHeaderProps) {
  return (
    <>
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-one-turq-d font-semibold text-[12px] hover:underline mb-3"
        aria-label="Vissza az inboxhoz"
      >
        <ArrowLeft size={14} />
        Vissza az inboxhoz
      </button>

      <div className="bg-gradient-to-r from-one-turq-l to-white border border-one-line rounded-one p-3 mb-4">
        <div className="flex flex-wrap items-start gap-2 mb-2">
          <div className="flex-1 min-w-0">
            <h1 className="text-[16px] font-bold text-one-ink leading-snug">{caseData.category_label}</h1>
            <code className="font-mono text-[11px] text-one-grey">#{caseData.case_id}</code>
          </div>
          <div className="flex items-center gap-2 flex-wrap shrink-0 pt-0.5">
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
