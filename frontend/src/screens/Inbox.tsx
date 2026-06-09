import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import type { InboxItem } from "../lib/types";
import { CaseBadgeRow } from "../components/CaseBadgeRow";
import { useSession } from "../state/session";
import { useToast } from "../state/toast";

const SORT_OPTIONS = [
  { value: "priority", label: "Prioritás" },
  { value: "sla", label: "SLA" },
  { value: "arrival", label: "Beérkezés" },
];
const FILTER_STORAGE_KEY = "jogos.inbox.filters";

interface InboxFilters {
  category: string;
  priority: string;
  status: string;
  channel: string;
  sortBy: string;
  search: string;
}

const SAVED_VIEWS: Array<{ id: string; label: string; filters: Partial<InboxFilters> }> = [
  { id: "urgent", label: "Sürgős", filters: { priority: "surgos", sortBy: "sla" } },
  { id: "escalated", label: "Eszkalált", filters: { status: "eszkalalva", sortBy: "sla" } },
  { id: "postal", label: "Postai/OCR", filters: { channel: "postal", sortBy: "arrival" } },
  { id: "mine", label: "Saját ügyek", filters: { sortBy: "sla" } },
];

function loadStoredFilters(searchParam: string): InboxFilters {
  const defaults: InboxFilters = { category: "", priority: "", status: "", channel: "", sortBy: "priority", search: searchParam };
  try {
    const stored = localStorage.getItem(FILTER_STORAGE_KEY);
    if (!stored) return defaults;
    const parsed = JSON.parse(stored) as Partial<InboxFilters>;
    return { ...defaults, ...parsed, search: searchParam || parsed.search || "" };
  } catch {
    return defaults;
  }
}

function useInboxKeyboard({
  items,
  activeIndex,
  setActiveIndex,
  onOpen,
  searchInputRef,
}: {
  items: InboxItem[];
  activeIndex: number;
  setActiveIndex: (value: number | ((prev: number) => number)) => void;
  onOpen: (caseId: string) => void;
  searchInputRef: React.RefObject<HTMLInputElement>;
}) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const editing = target?.tagName === "INPUT" || target?.tagName === "SELECT" || target?.tagName === "TEXTAREA";
      if (event.key === "/" && !editing) {
        event.preventDefault();
        searchInputRef.current?.focus();
      } else if (event.key === "ArrowDown" && !editing) {
        event.preventDefault();
        setActiveIndex((prev) => Math.min(items.length - 1, prev + 1));
      } else if (event.key === "ArrowUp" && !editing) {
        event.preventDefault();
        setActiveIndex((prev) => Math.max(0, prev - 1));
      } else if (event.key === "Enter" && !editing && items[activeIndex]) {
        event.preventDefault();
        onOpen(items[activeIndex].case_id);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [activeIndex, items, onOpen, searchInputRef, setActiveIndex]);
}

export function Inbox() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useSession();
  const { show } = useToast();
  const [items, setItems] = useState<InboxItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const searchInputRef = useRef<HTMLInputElement>(null);

  const initialFilters = useMemo(() => loadStoredFilters(searchParams.get("search") ?? ""), [searchParams]);
  const [category, setCategory] = useState(initialFilters.category);
  const [priority, setPriority] = useState(initialFilters.priority);
  const [status, setStatus] = useState(initialFilters.status);
  const [channel, setChannel] = useState(initialFilters.channel);
  const [sortBy, setSortBy] = useState(initialFilters.sortBy);
  const [search, setSearch] = useState(initialFilters.search);
  const [selectedCaseIds, setSelectedCaseIds] = useState<string[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);

  const currentParams = () => {
    const params: Record<string, string> = { sort_by: sortBy };
    if (category) params.category = category;
    if (priority) params.priority = priority;
    if (status) params.status = status;
    if (channel) params.channel = channel;
    if (search) params.search = search;
    return params;
  };

  const refresh = async () => {
    const res = await api.getInbox(currentParams());
    setItems(res.items);
  };

  useEffect(() => {
    setLoading(true);
    setError("");
    refresh()
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [category, priority, status, channel, sortBy, search]);

  useEffect(() => {
    localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify({ category, priority, status, channel, sortBy, search }));
  }, [category, priority, status, channel, sortBy, search]);

  useEffect(() => {
    setSelectedCaseIds((prev) => prev.filter((caseId) => items.some((item) => item.case_id === caseId)));
    setActiveIndex((prev) => Math.min(prev, Math.max(0, items.length - 1)));
  }, [items]);

  const openCase = (caseId: string) => navigate(`/case/${caseId}`);
  useInboxKeyboard({ items, activeIndex, setActiveIndex, onOpen: openCase, searchInputRef });

  const applySavedView = (filters: Partial<InboxFilters>) => {
    setCategory(filters.category ?? "");
    setPriority(filters.priority ?? "");
    setStatus(filters.status ?? "");
    setChannel(filters.channel ?? "");
    setSortBy(filters.sortBy ?? "priority");
    setSearch(filters.search ?? "");
  };

  const toggleSelected = (caseId: string) => {
    setSelectedCaseIds((prev) => prev.includes(caseId) ? prev.filter((id) => id !== caseId) : [...prev, caseId]);
  };

  const handleBulkStatus = async (targetStatus: string) => {
    if (!user || selectedCaseIds.length === 0) return;
    try {
      await Promise.all(selectedCaseIds.map((caseId) => api.updateStatus({ case_id: caseId, target_status: targetStatus, username: user.username, role: user.role })));
      show(`${selectedCaseIds.length} ügy frissítve`, "success");
      setSelectedCaseIds([]);
      await refresh();
    } catch (e) {
      show(e instanceof Error ? e.message : "Bulk művelet hiba", "error");
    }
  };

  const selectClass = "text-[12px] border border-one-line rounded-md px-2 py-1.5 bg-white text-one-ink focus:outline-none focus:ring-2 focus:ring-one-turq";

  return (
    <div>
      <h1 className="text-[16px] font-bold text-one-ink mb-4">Inbox - bejövő ügyek</h1>

      <SavedViewsBar onApply={applySavedView} />
      <BulkActionBar selectedCount={selectedCaseIds.length} onClear={() => setSelectedCaseIds([])} onStatus={handleBulkStatus} />

      <div className="flex flex-wrap gap-2 mb-4">
        <input
          ref={searchInputRef}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Keresés..."
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
          <option value="uj">Új</option>
          <option value="folyamatban">Folyamatban</option>
          <option value="eszkalalva">Eszkalált</option>
          <option value="jovahagyasra_var">Jóváhagyásra vár</option>
          <option value="lezarva">Lezárt</option>
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
      {loading && <div className="text-one-grey text-[12px]">Betöltés...</div>}

      {!loading && items.length === 0 && (
        <div className="text-one-grey text-center py-12 text-[13px]">Nincs megjeleníthető üzenet.</div>
      )}

      <div className="flex flex-col gap-2">
        {items.map((item, index) => (
          <div
            key={item.case_id}
            className={`bg-one-surface border rounded-one shadow-card p-3 flex items-start justify-between gap-3 hover:border-one-turq transition-colors ${activeIndex === index ? "border-one-turq" : "border-one-line"}`}
          >
            <input
              type="checkbox"
              checked={selectedCaseIds.includes(item.case_id)}
              onChange={() => toggleSelected(item.case_id)}
              className="mt-1 accent-one-turq"
              aria-label={`Kijelölés: ${item.subject}`}
            />
            <div className="flex-1 min-w-0" onClick={() => setActiveIndex(index)}>
              <CaseBadgeRow item={item} />
              <div className="mt-1 font-semibold text-[13px] text-one-ink truncate">{item.subject}</div>
              <div className="mt-1 flex flex-wrap gap-2 text-[10px] text-one-grey">
                <span>SLA: {item.sla_days_remaining} nap</span>
                <span>{item.assignee_username ? `Assignee: ${item.assignee_username}` : "Nincs kiosztva"}</span>
                {item.claimed_by_username && <span>Claim: {item.claimed_by_username}</span>}
              </div>
            </div>
            <button
              onClick={() => openCase(item.case_id)}
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

function SavedViewsBar({ onApply }: { onApply: (filters: Partial<InboxFilters>) => void }) {
  return (
    <div className="flex flex-wrap gap-2 mb-3">
      {SAVED_VIEWS.map((view) => (
        <button
          key={view.id}
          onClick={() => onApply(view.filters)}
          className="bg-white border border-one-line text-one-ink text-[11px] px-3 py-1.5 rounded-pill hover:bg-one-canvas"
        >
          {view.label}
        </button>
      ))}
    </div>
  );
}

function BulkActionBar({
  selectedCount,
  onClear,
  onStatus,
}: {
  selectedCount: number;
  onClear: () => void;
  onStatus: (status: string) => void;
}) {
  if (!selectedCount) return null;
  return (
    <div className="mb-3 bg-one-surface border border-one-line rounded-one p-2 flex items-center gap-2 text-[11px]">
      <span className="font-semibold">{selectedCount} ügy kijelölve</span>
      <button onClick={() => onStatus("folyamatban")} className="bg-white border border-one-line rounded-pill px-3 py-1 hover:bg-one-canvas">Folyamatban</button>
      <button onClick={() => onStatus("eszkalalva")} className="bg-white border border-one-line rounded-pill px-3 py-1 hover:bg-one-canvas">Eszkalálás</button>
      <button onClick={onClear} className="ml-auto text-one-grey hover:text-one-ink">Kijelölés törlése</button>
    </div>
  );
}
