import type { MutableRefObject } from "react";
import type { ChunkItem, SourceRef, UnresolvedReference } from "../../lib/types";
import { Card } from "../Card";
import { ProvenanceBadge, RichSourceCard, SourceCard } from "../SourceCard";

interface CaseSourcesPanelProps {
  sources: SourceRef[];
  chunks: ChunkItem[];
  unresolvedRefs?: UnresolvedReference[];
  sourceRefs: MutableRefObject<Record<string, HTMLDivElement | null>>;
}

export function formatUnresolvedRef(ref: UnresolvedReference): string {
  if (typeof ref === "string") return ref;
  const primary = ref.paragraph ?? ref.raw ?? JSON.stringify(ref);
  return ref.doc_hint ? `${primary} (${ref.doc_hint})` : String(primary);
}

export function UnresolvedReferencesPanel({ refs }: { refs: UnresolvedReference[] }) {
  if (!refs.length) return null;
  return (
    <div className="mb-3 rounded-md border border-status-esc-fg bg-status-esc-bg p-2 text-[11px] text-status-esc-fg">
      <div className="font-semibold mb-1">Be nem húzható hivatkozások</div>
      <div className="flex flex-wrap gap-1">
        {refs.map((ref, index) => (
          <span key={`${formatUnresolvedRef(ref)}-${index}`} className="rounded-full bg-white/70 px-2 py-0.5 text-[10px]">
            {formatUnresolvedRef(ref)}
          </span>
        ))}
      </div>
    </div>
  );
}

export function CaseSourcesPanel({ sources, chunks, unresolvedRefs = [], sourceRefs }: CaseSourcesPanelProps) {
  return (
    <Card title="Források">
      <UnresolvedReferencesPanel refs={unresolvedRefs} />
      {sources.length > 0 ? (
        sources.map((source) => (
          <div key={source.ref} ref={(el) => { sourceRefs.current[source.ref] = el; }}>
            <RichSourceCard source={source} id={`source-${source.ref}`} />
          </div>
        ))
      ) : chunks.length === 0 ? (
        <p className="text-one-grey text-[11px]">Nincs forrás.</p>
      ) : (
        chunks.map((chunk) => (
          <div key={chunk.chunk_id} ref={(el) => { sourceRefs.current[chunk.chunk_id] = el; }}>
            <div className="mb-1">
              <ProvenanceBadge source={chunk.retrieval_source} score={chunk.score} />
            </div>
            <SourceCard chunk={chunk} id={`source-${chunk.chunk_id}`} />
          </div>
        ))
      )}
    </Card>
  );
}
