import type { EscalationState, TimelineStep } from "../../lib/types";
import { AgentTimeline } from "../AgentTimeline";

interface CaseTimelinePanelProps {
  hasTimeline: boolean;
  steps: TimelineStep[];
  escalation: EscalationState | null;
  onToggle?: (open: boolean) => void;
  onEscalateToSupervisor?: () => void;
  escalationPending?: boolean;
  alreadyEscalated?: boolean;
  processing?: boolean;
}

export function CaseTimelinePanel({
  hasTimeline,
  steps,
  escalation,
  onToggle,
  onEscalateToSupervisor,
  escalationPending = false,
  alreadyEscalated = false,
  processing = false,
}: CaseTimelinePanelProps) {
  const escalationDisabled = !onEscalateToSupervisor || escalationPending || alreadyEscalated;

  return (
    <div className="min-w-0">
      {!hasTimeline ? (
        <div className="bg-one-surface border border-one-line rounded-one p-3 text-[11px] text-one-grey">
          {processing ? "Varakozas az elso agent-visszajelzesre..." : "Az idovonal az agent futasa utan jelenik meg."}
        </div>
      ) : (
        <AgentTimeline steps={steps} defaultOpen={true} onToggle={onToggle} />
      )}
      {escalation?.required && hasTimeline ? (
        <div className="mt-3 bg-status-esc-bg border border-status-esc-fg rounded-one p-3 text-[11px]">
          <p className="font-semibold text-status-esc-fg mb-2">Eszkalacio szukseges</p>
          <button
            onClick={onEscalateToSupervisor}
            disabled={escalationDisabled}
            className="bg-status-esc-fg text-white text-[10px] px-3 py-1.5 rounded-pill font-bold hover:opacity-90 transition-opacity disabled:opacity-60"
          >
            {alreadyEscalated ? "Supervisor sorban" : escalationPending ? "Kuldes..." : "Eszkalacio supervisorhoz ->"}
          </button>
        </div>
      ) : null}
    </div>
  );
}
