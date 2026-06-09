import type { MutableRefObject } from "react";
import type { ChunkItem, SourceRef } from "../../lib/types";
import { Card } from "../Card";
import { RichSourceCard, SourceCard } from "../SourceCard";

interface CaseSourcesPanelProps {
  sources: SourceRef[];
  chunks: ChunkItem[];
  sourceRefs: MutableRefObject<Record<string, HTMLDivElement | null>>;
}

export function CaseSourcesPanel({ sources, chunks, sourceRefs }: CaseSourcesPanelProps) {
  return (
    <Card title="Forrasok">
      {sources.length > 0 ? (
        sources.map((source) => (
          <div key={source.ref} ref={(el) => { sourceRefs.current[source.ref] = el; }}>
            <RichSourceCard source={source} id={`source-${source.ref}`} />
          </div>
        ))
      ) : chunks.length === 0 ? (
        <p className="text-one-grey text-[11px]">Nincs forras.</p>
      ) : (
        chunks.map((chunk) => (
          <div key={chunk.chunk_id} ref={(el) => { sourceRefs.current[chunk.chunk_id] = el; }}>
            <SourceCard chunk={chunk} id={`source-${chunk.chunk_id}`} />
          </div>
        ))
      )}
    </Card>
  );
}
