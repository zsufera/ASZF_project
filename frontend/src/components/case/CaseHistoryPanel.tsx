import type { HistoryItem } from "../../lib/types";
import { Card } from "../Card";
import { HistoryCard } from "../HistoryCard";

interface CaseHistoryPanelProps {
  items: HistoryItem[];
  isRepeated: boolean;
}

export function CaseHistoryPanel({ items, isRepeated }: CaseHistoryPanelProps) {
  return (
    <Card title="Előzmények">
      <HistoryCard items={items} isRepeated={isRepeated} />
    </Card>
  );
}
