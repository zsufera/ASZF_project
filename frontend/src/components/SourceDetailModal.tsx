import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { AszfKnowledgeItem, SourceRef } from "../lib/types";
import { Modal } from "./Modal";
import { ProvenanceBadge } from "./SourceCard";

interface SourceDetailModalProps {
  source: SourceRef;
  onClose: () => void;
}

/** Felugró ablak egy forrás teljes ÁSZF-szövegével (a chunk_id alapján lekérve). */
export function SourceDetailModal({ source, onClose }: SourceDetailModalProps) {
  const [item, setItem] = useState<AszfKnowledgeItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api.getAszfSection(source.chunk_id)
      .then((res) => { if (active) setItem(res.item); })
      .catch((e) => { if (active) setError(e instanceof Error ? e.message : "Betöltési hiba"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [source.chunk_id]);

  const title = `${source.dok_cim ?? source.dok_tipus ?? "Forrás"}${source.paragrafus ? ` · §${source.paragrafus}` : ""}`;
  const fullText = item?.text || item?.quote || source.idezet || "";

  return (
    <Modal title={title} onClose={onClose} widthClass="max-w-2xl">
      <div className="space-y-3 text-[12px]">
        <div className="flex flex-wrap items-center gap-2 text-[10px] text-one-grey">
          <span className="font-bold bg-one-turq-l text-one-turq-d border border-one-turq rounded-full px-2 py-0.5">{source.ref}</span>
          <ProvenanceBadge source={source.retrieval_source} score={source.score} />
          {source.dok_tipus ? <span>{source.dok_tipus}</span> : null}
          {source.oldalszam !== undefined ? <span>· {source.oldalszam}. oldal</span> : null}
        </div>

        {loading ? (
          <p className="text-one-grey">Betöltés…</p>
        ) : error ? (
          <p className="text-status-urgent-fg">{error}</p>
        ) : (
          <div className="whitespace-pre-wrap leading-relaxed text-one-ink max-h-[55vh] overflow-auto border border-one-line rounded-md p-4 bg-one-canvas">
            {fullText || "Nincs elérhető szöveg ehhez a forráshoz."}
          </div>
        )}

        {source.magyarazat ? (
          <div className="rounded-md bg-one-turq-l/40 border border-one-line p-2 text-[11px] text-one-grey">
            <span className="font-semibold text-one-ink">Relevancia: </span>{source.magyarazat}
          </div>
        ) : null}

        {item?.cross_refs?.length ? (
          <div>
            <div className="text-[10px] uppercase text-one-grey font-semibold tracking-wider mb-1">Kereszthivatkozások</div>
            <div className="flex flex-wrap gap-1">
              {item.cross_refs.map((ref) => (
                <span key={ref} className="rounded-full bg-one-canvas border border-one-line px-2 py-0.5 text-[10px] text-one-grey">{ref}</span>
              ))}
            </div>
          </div>
        ) : null}

        <code className="block text-[10px] text-one-grey break-all">{source.chunk_id}</code>
      </div>
    </Modal>
  );
}
