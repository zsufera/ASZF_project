import { useState, useEffect } from "react";
import type { TimelineStep } from "../lib/types";
import { TimelineStepItem } from "./TimelineStep";

interface AgentTimelineProps {
  steps: TimelineStep[];
  defaultOpen?: boolean;
  onToggle?: (open: boolean) => void;
}

export function AgentTimeline({ steps, defaultOpen = true, onToggle }: AgentTimelineProps) {
  const [open, setOpen] = useState(() => {
    try { return JSON.parse(localStorage.getItem("timeline.open") ?? "true") as boolean; } catch { return defaultOpen; }
  });

  useEffect(() => {
    try { localStorage.setItem("timeline.open", JSON.stringify(open)); } catch {}
    onToggle?.(open);
  }, [open, onToggle]);

  return (
    <div className="bg-one-surface border border-one-line rounded-one shadow-card">
      <button
        className="w-full flex items-center justify-between px-3 py-2 text-[10px] uppercase tracking-wider text-one-grey font-semibold border-b border-one-line focus-visible:ring-2 focus-visible:ring-one-turq"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label="Agent-idővonal ki/becsukása"
      >
        <span>⚙ Agent-idővonal</span>
        <span>{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="p-3 divide-y divide-one-line animate-fade-in">
          {steps.length === 0 ? (
            <p className="text-one-grey text-[11px] py-2">Nincs adat.</p>
          ) : (
            steps.map((s, i) => <TimelineStepItem key={i} step={s} />)
          )}
        </div>
      )}
    </div>
  );
}
