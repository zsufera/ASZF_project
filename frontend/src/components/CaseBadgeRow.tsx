import { Badge } from "./Badge";
import type { InboxItem } from "../lib/types";

export function CaseBadgeRow({ item }: { item: Pick<InboxItem, "category_label" | "priority" | "confidence" | "escalated" | "channel_label" | "status_label" | "sla_days_remaining"> }) {
  return (
    <div className="flex flex-wrap gap-1">
      <Badge kind="category" value={item.category_label} />
      {item.priority === "surgos" && <Badge kind="priority" value="SÜRGŐS" />}
      {item.escalated && <Badge kind="escalation" value="Eszkalált" />}
      {item.confidence < 0.7 && <Badge kind="confidence" value={item.confidence} />}
      <Badge kind="channel" value={item.channel_label} />
      <Badge kind="status" value={item.status_label} />
      <Badge kind="sla" value={item.sla_days_remaining} />
    </div>
  );
}
