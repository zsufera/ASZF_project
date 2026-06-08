import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import type { InboxItem } from "../lib/types";
import { CaseBadgeRow } from "../components/CaseBadgeRow";

const SORT_OPTIONS = [
  { value: "priority", label: "Prioritás" },
  { value: "sla", label: "SLA" },
  { value: "arrival", label: "Beérkezés" },
];

export function Inbox() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [items, setItems] = useState<InboxItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [category, setCategory] = useState("");
  const [priority, setPriority] = useState("");
  const [status, setStatus] = useState("");
  const [channel, setChannel] = useState("");
  const [sortBy, setSortBy] = useState("priority");
  const [search, setSearch] = useState(searchParams.get("search") ?? "");

  useEffect(() => {
    setLoading(true);
    setError("");
    const params: Record<string, string> = { sort_by: sortBy };
    if (category) params.category = category;
    if (priority) params.priority = priority;
    if (status) params.status = status;
    if (channel) params.channel = channel;
    if (search) params.search = search;

    api.getInbox(params)
      .then((r) => setItems(r.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [category, priority, status, channel, sortBy, search]);

  const selectClass = "text-[12px] border border-one-line rounded-md px-2 py-1.5 bg-white text-one-ink focus:outline-none focus:ring-2 focus:ring-one-turq";

  return (
    <div>
      <h1 className="text-[16px] font-bold text-one-ink mb-4">Inbox — bejövő ügyek</h1>

      <div className="flex flex-wrap gap-2 mb-4">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Keresés…"
          className="text-[12px] border border-one-line rounded-md px-2 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-one-turq"
          aria-label="Keresés"
        />
        <select value={category} onChange={(e) => setCategory(e.target.value)} className={selectClass} aria-label="Kategória szűrő">
          <option value="">Kategória</option>
          <option value="szamlazas">Számlázás</option>
          <option value="dijemeles">Díjemelés</option>
          <option value="felmondas">Felmondás</option>
        </select>
        <select value={priority} onChange={(e) => setPriority(e.target.value)} className={selectClass} aria-label="Prioritás szűrő">
          <option value="">Prioritás</option>
          <option value="surgos">SÜRGŐS</option>
          <option value="normal">Normál</option>
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)} className={selectClass} aria-label="Státusz szűrő">
          <option value="">Státusz</option>
          <option value="nyitott">Nyitott</option>
          <option value="lezart">Lezárt</option>
        </select>
        <select value={channel} onChange={(e) => setChannel(e.target.value)} className={selectClass} aria-label="Csatorna szűrő">
          <option value="">Csatorna</option>
          <option value="email">Email</option>
          <option value="chat">Chat</option>
          <option value="postal">Postai</option>
        </select>
        <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className={selectClass} aria-label="Rendezés">
          {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      {error && <div className="text-status-urgent-fg text-[12px] mb-3">{error}</div>}
      {loading && <div className="text-one-grey text-[12px]">Betöltés…</div>}

      {!loading && items.length === 0 && (
        <div className="text-one-grey text-center py-12 text-[13px]">Nincs megjeleníthető üzenet.</div>
      )}

      <div className="flex flex-col gap-2">
        {items.map((item) => (
          <div
            key={item.case_id}
            className="bg-one-surface border border-one-line rounded-one shadow-card p-3 flex items-start justify-between gap-3 hover:border-one-turq transition-colors"
          >
            <div className="flex-1 min-w-0">
              <CaseBadgeRow item={item} />
              <div className="mt-1 font-semibold text-[13px] text-one-ink truncate">{item.subject}</div>
            </div>
            <button
              onClick={() => navigate(`/case/${item.case_id}`)}
              className="bg-one-turq text-[#04201f] font-bold text-[11px] px-3 py-1.5 rounded-pill hover:bg-one-turq-d transition-colors shrink-0"
              aria-label={`Megnyitás: ${item.subject}`}
            >
              Megnyitás
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
