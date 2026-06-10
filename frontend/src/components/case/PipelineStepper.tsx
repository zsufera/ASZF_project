import { CheckCircle2, Circle, XCircle } from "lucide-react";
import type { TimelineStep } from "../../lib/types";
import { FIELD_LABELS, PIPELINE_STEPS, STEP_META, formatFieldValue, stepLabel } from "../../lib/agentSteps";

interface PipelineStepperProps {
  steps: TimelineStep[];
}

type StepStatus = "done" | "error" | "pending";

function getStatus(step: string, steps: TimelineStep[]): StepStatus {
  const found = steps.find((s) => s.step === step);
  if (!found) return "pending";
  if (found.status === "error") return "error";
  return "done";
}

export function PipelineStepper({ steps }: PipelineStepperProps) {
  if (!steps.length) return null;

  const completedStep = steps[steps.length - 1]?.step;
  const completedIndex = PIPELINE_STEPS.indexOf(completedStep ?? "");

  return (
    <div className="mb-4 bg-one-surface border border-one-line rounded-one px-4 py-3 overflow-x-auto">
      <div className="flex items-center gap-0 min-w-max">
        {PIPELINE_STEPS.map((stepKey, index) => {
          const status = getStatus(stepKey, steps);
          const meta = STEP_META[stepKey];
          const foundStep = steps.find((s) => s.step === stepKey);
          const isLast = index === PIPELINE_STEPS.length - 1;

          return (
            <div key={stepKey} className="flex items-center">
              <div className="relative group flex flex-col items-center">
                <StepIcon status={status} active={index === completedIndex} />
                <span className={`mt-1 text-[9px] whitespace-nowrap max-w-[72px] text-center leading-tight ${status === "done" ? "text-one-ink font-semibold" : "text-one-grey"}`}>
                  {meta?.label ?? stepLabel(stepKey)}
                </span>
                {foundStep && (
                  <StepTooltip step={stepKey} output={foundStep.output} />
                )}
              </div>
              {!isLast && (
                <div className={`w-8 h-px mx-1 mt-[-16px] shrink-0 ${status === "done" ? "bg-kpi-ok" : "bg-one-line"}`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StepIcon({ status, active }: { status: StepStatus; active: boolean }) {
  if (status === "error") return <XCircle size={16} className="text-kpi-bad" />;
  if (status === "done") return <CheckCircle2 size={16} className="text-kpi-ok" />;
  return <Circle size={16} className={active ? "text-one-turq animate-pulse" : "text-one-line"} />;
}

function StepTooltip({ step, output }: { step: string; output: Record<string, unknown> }) {
  const meta = STEP_META[step];
  const fields = meta?.fields ?? Object.keys(output).slice(0, 4);

  return (
    <div className="pointer-events-none absolute bottom-[calc(100%+8px)] left-1/2 -translate-x-1/2 z-50 hidden group-hover:block w-56">
      <div className="bg-one-ink text-white rounded-one shadow-lg text-[10px] p-3">
        <p className="font-bold text-[11px] mb-1">{meta?.label ?? step}</p>
        {meta?.explain && <p className="text-white/70 mb-2 leading-snug">{meta.explain}</p>}
        <div className="space-y-1">
          {fields.map((field) => {
            if (!(field in output)) return null;
            return (
              <div key={field} className="flex justify-between gap-3">
                <span className="text-white/60">{FIELD_LABELS[field] ?? field}</span>
                <span className="font-semibold text-right">{formatFieldValue(field, output[field])}</span>
              </div>
            );
          })}
        </div>
        <div className="absolute bottom-[-5px] left-1/2 -translate-x-1/2 w-2.5 h-2.5 bg-one-ink rotate-45" />
      </div>
    </div>
  );
}
