import type { CustomerCandidateItem } from "../../lib/types";
import { Card } from "../Card";
import { CustomerCandidateList } from "../CustomerCandidate";

interface CaseCustomerPanelProps {
  candidates: CustomerCandidateItem[];
  selected: string | null;
  onSelect: (customerId: string | null) => void;
}

export function CaseCustomerPanel({ candidates, selected, onSelect }: CaseCustomerPanelProps) {
  return (
    <Card title="Ugyfeltorzs-jeloltek">
      <CustomerCandidateList candidates={candidates} selected={selected} onSelect={onSelect} />
    </Card>
  );
}
