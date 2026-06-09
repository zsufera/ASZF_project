import { useState } from "react";
import type { ChunkItem, RetrievalSource, SourceRef } from "../lib/types";

interface SourceCardProps {
  chunk: ChunkItem;
  id?: string;
  onJump?: () => void;
}

export function SourceCard({ chunk, id, onJump }: SourceCardProps) {
  const [showExplain, setShowExplain] = useState(false);
  const quote = chunk.quote ?? chunk.idezet ?? "";

  return (
    <div
      id={id}
      className="border-l-2 border-one-turq bg-[#FbFdfd] rounded-r-md px-3 py-2 mb-2 text-[11px] transition-all duration-150"
    >
      <div className="flex items-center justify-between mb-1">
        <span className="font-bold text-one-turq-d">§ {chunk.paragrafus} · {chunk.dok_tipus}</span>
        {onJump && (
          <button onClick={onJump} className="text-one-turq-d hover:underline ml-2" aria-label="Ugrás a teljes szakaszra">⤴</button>
        )}
      </div>
      <div className="flex flex-wrap gap-1 mb-1">
        <ProvenanceBadge source={chunk.retrieval_source} score={chunk.score} />
      </div>
      {quote && <p className="italic text-[#33403f] mb-1">„{quote}"</p>}
      {chunk.kozertheto_magyarazat && (
        <>
          <button
            onClick={() => setShowExplain((v) => !v)}
            className="text-[9px] text-one-turq-d border border-one-turq rounded-full px-2 py-0.5 hover:bg-one-turq-l transition-colors"
            aria-expanded={showExplain}
          >
            {showExplain ? "Elrejt" : "Közérthető magyarázat"}
          </button>
          {showExplain && <p className="mt-2 text-one-grey text-[10px] animate-fade-in">{chunk.kozertheto_magyarazat}</p>}
        </>
      )}
    </div>
  );
}

function provenanceLabel(source?: RetrievalSource): string {
  if (!source) return "forrás";
  const labels: Record<string, string> = {
    qdrant_semantic: "szemantikus",
    hybrid_local: "hibrid",
    reference_closure: "hivatkozás-closure",
    parent_context: "szülő kontextus",
    auto_merged: "összevont szakasz",
    empty: "nincs találat",
  };
  return labels[String(source)] ?? String(source);
}

export function ProvenanceBadge({ source, score }: { source?: RetrievalSource; score?: number }) {
  const label = provenanceLabel(source);
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-one-line bg-one-canvas px-2 py-0.5 text-[9px] text-one-grey">
      <span>{label}</span>
      {score !== undefined ? <span>{score.toFixed(2)}</span> : null}
    </span>
  );
}

function relevanceLabel(score?: number): string | null {
  if (score === undefined || score === null) return null;
  if (score >= 0.75) return "magas";
  if (score >= 0.4) return "közepes";
  return "alacsony";
}

interface RichSourceCardProps {
  source: SourceRef;
  id?: string;
}

/** Gazdag, lenyitható forrás-kártya a SourceRef adatokból. */
export function RichSourceCard({ source, id }: RichSourceCardProps) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const rel = relevanceLabel(source.score);

  const copyId = () => {
    navigator.clipboard?.writeText(source.chunk_id).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    }).catch(() => {});
  };

  return (
    <div
      id={id}
      className={`border-l-2 rounded-r-md px-3 py-2 mb-2 text-[11px] transition-all duration-150 ${source.used ? "border-one-turq bg-[#FbFdfd]" : "border-one-line bg-white opacity-70"}`}
    >
      <button onClick={() => setOpen((v) => !v)} className="w-full flex items-center justify-between text-left" aria-expanded={open}>
        <span className="flex items-center gap-2 min-w-0">
          <span className="text-[9px] font-bold bg-one-turq-l text-one-turq-d border border-one-turq rounded-full px-1.5 py-0.5 flex-none">{source.ref}</span>
          <span className="font-semibold text-one-ink truncate">{source.dok_cim ?? source.dok_tipus ?? "Forrás"}{source.paragrafus ? ` · §${source.paragrafus}` : ""}</span>
        </span>
        <span className="flex items-center gap-1 flex-none ml-2">
          {rel && <span className="text-[9px] text-one-grey">{rel}</span>}
          <span className="text-one-grey">{open ? "▾" : "▸"}</span>
        </span>
      </button>

      {open && (
        <div className="mt-2 animate-fade-in">
          <div className="flex flex-wrap gap-2 text-[9px] text-one-grey mb-1">
            <ProvenanceBadge source={source.retrieval_source} score={source.score} />
            {source.dok_tipus && <span>{source.dok_tipus}</span>}
            {source.oldalszam !== undefined && <span>· {source.oldalszam}. oldal</span>}
          </div>
          {source.idezet && <p className="italic text-[#33403f] mb-1">„{source.idezet}"</p>}
          {source.magyarazat && <p className="text-one-grey text-[10px] mb-1">{source.magyarazat}</p>}
          <button onClick={copyId} className="text-[9px] text-one-turq-d hover:underline" aria-label="chunk_id másolása">
            {copied ? "✓ másolva" : `id: ${source.chunk_id}`}
          </button>
        </div>
      )}
    </div>
  );
}
