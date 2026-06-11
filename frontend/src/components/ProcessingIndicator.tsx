import type { TimelineStep } from "../lib/types";
import { TimelineStepItem } from "./TimelineStep";

interface ProcessingIndicatorProps {
  active: boolean;
  steps?: TimelineStep[];
}

export function ProcessingIndicator({ active, steps = [] }: ProcessingIndicatorProps) {
  if (!active) return null;

  return (
    <div className="bg-one-surface border border-one-line rounded-one p-3 animate-fade-in" role="status" aria-live="polite">
      <div className="flex items-center gap-2 text-[11px] font-semibold text-one-ink mb-2">
        <span className="animate-spin text-one-turq-d" aria-hidden="true">⟳</span>
        Az agent dolgozik…
      </div>
      {steps.length ? (
        <div className="divide-y divide-one-line">
          {steps.map((step, index) => (
            <TimelineStepItem key={`${step.step}-${index}`} step={step} />
          ))}
        </div>
      ) : (
        <p className="text-[10px] text-one-grey">Várakozás az első agent-visszajelzésre…</p>
      )}
    </div>
  );
}
