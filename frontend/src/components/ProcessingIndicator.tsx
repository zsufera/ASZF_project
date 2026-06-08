import { useState, useEffect } from "react";
import { PIPELINE_STEPS, stepLabel } from "../lib/agentSteps";

interface ProcessingIndicatorProps {
  active: boolean;
  /** Mennyi idő alatt lépjen a következő szakaszra (szimulált). */
  intervalMs?: number;
}

/**
 * A feldolgozás alatt végigfut az agent pipeline szakaszain (szimulált, idő-alapú).
 * Nem valós token-stream: a backend szinkron, a végén adja vissza a teljes idővonalat.
 */
export function ProcessingIndicator({ active, intervalMs = 3500 }: ProcessingIndicatorProps) {
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    if (!active) { setIdx(0); return; }
    setIdx(0);
    const id = setInterval(() => {
      setIdx((i) => Math.min(i + 1, PIPELINE_STEPS.length - 1));
    }, intervalMs);
    return () => clearInterval(id);
  }, [active, intervalMs]);

  if (!active) return null;

  return (
    <div className="bg-one-surface border border-one-line rounded-one p-3 animate-fade-in" role="status" aria-live="polite">
      <div className="flex items-center gap-2 text-[11px] font-semibold text-one-ink mb-2">
        <span className="animate-spin text-one-turq-d" aria-hidden="true">⟳</span>
        Az agent dolgozik…
      </div>
      <ul className="space-y-1">
        {PIPELINE_STEPS.map((s, i) => (
          <li
            key={s}
            className={`flex items-center gap-2 text-[10px] ${
              i < idx ? "text-one-grey" : i === idx ? "text-one-turq-d font-semibold" : "text-one-grey opacity-40"
            }`}
          >
            <span className="w-3 flex-none text-center" aria-hidden="true">
              {i < idx ? "✓" : i === idx ? "▸" : "·"}
            </span>
            <span>{stepLabel(s)}</span>
          </li>
        ))}
      </ul>
      <p className="text-[9px] text-one-grey mt-2">A feldolgozás a modelltől függően akár egy percig is tarthat.</p>
    </div>
  );
}
