import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import type { AszfKnowledgeGroup, AszfKnowledgeItem } from "../lib/types";

export function Knowledge() {
  const [groups, setGroups] = useState<AszfKnowledgeGroup[]>([]);
  const [selected, setSelected] = useState<AszfKnowledgeItem | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<AszfKnowledgeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getAszfTree()
      .then((res) => {
        setGroups(res.items);
        const first = res.items.flatMap((group) => group.items)[0];
        if (first) return api.getAszfSection(first.chunk_id).then((section) => setSelected(section.item));
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Tudástár hiba"))
      .finally(() => setLoading(false));
  }, []);

  const total = useMemo(() => groups.reduce((sum, group) => sum + group.count, 0), [groups]);

  const openSection = async (chunkId: string) => {
    try {
      const res = await api.getAszfSection(chunkId);
      setSelected(res.item);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Szakasz betöltési hiba");
    }
  };

  const handleSearch = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!query.trim()) { setResults([]); return; }
    try {
      const res = await api.searchAszf(query);
      setResults(res.items);
      if (res.items[0]) await openSection(res.items[0].chunk_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Keresési hiba");
    }
  };

  if (loading) return <div className="text-one-grey p-8">Betöltés...</div>;

  return (
    <div>
      <div className="flex items-center justify-between gap-3 mb-4">
        <div>
          <h1 className="text-[16px] font-bold text-one-ink">Tudástár</h1>
          <p className="text-[11px] text-one-grey">{groups.length} szakaszcsoport · {total} chunk</p>
        </div>
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="§, kulcsszó vagy dokumentum..."
            className="w-72 border border-one-line rounded-md px-3 py-1.5 text-[12px] focus:outline-none focus:ring-2 focus:ring-one-turq"
            aria-label="ÁSZF keresés"
          />
          <button className="bg-one-turq text-[#04201f] font-bold text-[11px] px-3 py-1.5 rounded-pill hover:bg-one-turq-d">
            Keresés
          </button>
        </form>
      </div>

      {error && <div className="text-status-urgent-fg text-[12px] mb-3">{error}</div>}

      <div className="grid grid-cols-[280px_1fr_280px] gap-4">
        <aside className="bg-one-surface border border-one-line rounded-one overflow-hidden">
          <div className="px-3 py-2 border-b border-one-line text-[10px] uppercase text-one-grey font-semibold tracking-wider">Szakaszfa</div>
          <div className="max-h-[calc(100vh-170px)] overflow-auto divide-y divide-one-line">
            {groups.map((group) => (
              <section key={group.section} className="p-2">
                <div className="text-[11px] font-semibold text-one-ink mb-1">{group.label} <span className="text-one-grey">({group.count})</span></div>
                <div className="flex flex-col gap-1">
                  {group.items.map((item) => (
                    <button
                      key={item.chunk_id}
                      onClick={() => openSection(item.chunk_id)}
                      className={`text-left rounded-md px-2 py-1 text-[10px] hover:bg-one-canvas ${selected?.chunk_id === item.chunk_id ? "bg-one-turq-l text-one-turq-d font-semibold" : "text-one-grey"}`}
                    >
                      §{item.paragrafus || "-"} · {item.dok_tipus || "ÁSZF"}
                    </button>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </aside>

        <main className="bg-one-surface border border-one-line rounded-one p-4 min-h-[420px]">
          {selected ? (
            <>
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <h2 className="text-[15px] font-semibold text-one-ink">§{selected.paragrafus || "-"}</h2>
                  <p className="text-[11px] text-one-grey">{selected.dok_cim || selected.dok_tipus || "Dokumentum"} · oldal {selected.oldalszam ?? "-"}</p>
                </div>
                <code className="text-[10px] text-one-grey bg-one-canvas rounded px-2 py-1">{selected.chunk_id}</code>
              </div>
              <div className="whitespace-pre-wrap text-[12px] leading-relaxed text-one-ink">
                {selected.text || selected.quote || "Nincs elérhető szöveg ehhez a szakaszhoz."}
              </div>
              {(selected.cross_refs?.length ?? 0) > 0 && (
                <div className="mt-4 border-t border-one-line pt-3">
                  <div className="text-[10px] uppercase text-one-grey font-semibold tracking-wider mb-2">Kereszthivatkozások</div>
                  <div className="flex flex-wrap gap-1">
                    {(selected.cross_refs ?? []).map((ref) => (
                      <span key={ref} className="rounded-full bg-one-canvas border border-one-line px-2 py-0.5 text-[10px] text-one-grey">
                        {ref}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="text-one-grey text-[12px]">Válassz egy ÁSZF-szakaszt.</p>
          )}
        </main>

        <aside className="bg-one-surface border border-one-line rounded-one overflow-hidden">
          <div className="px-3 py-2 border-b border-one-line text-[10px] uppercase text-one-grey font-semibold tracking-wider">Találatok</div>
          <div className="max-h-[calc(100vh-170px)] overflow-auto divide-y divide-one-line">
            {results.length ? results.map((item) => (
              <button key={item.chunk_id} onClick={() => openSection(item.chunk_id)} className="block w-full text-left p-3 hover:bg-one-canvas">
                <div className="text-[11px] font-semibold text-one-ink">§{item.paragrafus || "-"}</div>
                <div className="text-[10px] text-one-grey line-clamp-3">{item.quote}</div>
              </button>
            )) : (
              <p className="p-3 text-[11px] text-one-grey">Nincs aktív keresés.</p>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
