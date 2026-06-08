import { Fragment } from "react";
import type { SourceRef } from "../lib/types";

interface InlineAnswerProps {
  body: string;
  sources?: SourceRef[];
  onCite?: (ref: string) => void;
}

const MARKER = /\[S\d+\]/g;

/**
 * A body szövegben a [Sn] jelölőket kattintható türkiz chip-ekké alakítja.
 * Ismeretlen ref (nincs a sources között) nem jelenik meg nyersen.
 */
export function InlineAnswer({ body, sources, onCite }: InlineAnswerProps) {
  const validRefs = new Set((sources ?? []).map((s) => s.ref));
  const parts = body.split(MARKER);
  const markers = body.match(MARKER) ?? [];

  return (
    <div className="text-[12px] leading-relaxed whitespace-pre-wrap">
      {parts.map((part, i) => {
        const marker = markers[i]; // a part UTÁN következő jelölő (ha van)
        const ref = marker ? marker.slice(1, -1) : null;
        return (
          <Fragment key={i}>
            {part}
            {ref && validRefs.has(ref) ? (
              <button
                onClick={() => onCite?.(ref)}
                className="inline-flex items-center align-baseline mx-0.5 text-[9px] font-bold bg-one-turq-l text-one-turq-d border border-one-turq rounded-full px-1.5 py-0.5 hover:bg-one-turq hover:text-[#04201f] transition-colors"
                aria-label={`Forrás ${ref}`}
              >
                {ref}
              </button>
            ) : null}
          </Fragment>
        );
      })}
    </div>
  );
}
