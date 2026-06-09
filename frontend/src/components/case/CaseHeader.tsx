import type { Case } from "../../lib/types";
import { Badge } from "../Badge";

interface CaseHeaderProps {
  caseData: Case;
  onBack: () => void;
}

export function CaseHeader({ caseData, onBack }: CaseHeaderProps) {
  return (
    <>
      <div className="flex items-center gap-2 mb-3">
        <button
          onClick={onBack}
          className="text-one-turq-d font-semibold text-[12px] hover:underline"
          aria-label="Vissza az inboxhoz"
        >
          ← Vissza az inboxhoz
        </button>
      </div>
      <div className="bg-gradient-to-r from-one-turq-l to-white border border-one-line rounded-one p-3 mb-4 flex flex-wrap items-center gap-2">
        <span className="font-bold text-[15px]">Ügy #{caseData.case_id}</span>
        <Badge kind="category" value={caseData.category_label} />
        {caseData.priority === "surgos" ? <Badge kind="priority" value="SÜRGŐS" /> : null}
        {caseData.escalated ? <Badge kind="escalation" value="Eszkalált" /> : null}
        {caseData.confidence < 0.7 ? <Badge kind="confidence" value={caseData.confidence} /> : null}
        <span className="ml-auto text-one-grey text-[11px]">Email: {caseData.sender_email_display}</span>
        <span className="bg-white border border-one-line rounded-lg px-2 py-0.5 text-[11px] font-semibold">
          SLA: {caseData.sla_days_remaining} nap
        </span>
      </div>
    </>
  );
}
