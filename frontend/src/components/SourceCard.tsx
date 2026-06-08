import { useState } from "react";
import type { ChunkItem } from "../lib/types";

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
          <button
            onClick={onJump}
            className="text-one-turq-d hover:underline ml-2"
            aria-label="Ugrás a teljes szakaszra"
          >
            ⤴
          </button>
        )}
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
          {showExplain && (
            <p className="mt-2 text-one-grey text-[10px] animate-fade-in">{chunk.kozertheto_magyarazat}</p>
          )}
        </>
      )}
    </div>
  );
}
