import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import type { Role } from "../lib/types";

interface CommandItem {
  id: string;
  label: string;
  hint: string;
  path: string;
  roles?: Role[];
}

export const commandRegistry: CommandItem[] = [
  { id: "inbox", label: "Inbox megnyitása", hint: "Ügylista", path: "/inbox" },
  { id: "new-case", label: "Új ügy", hint: "Kézi ügyfelvétel", path: "/new" },
  { id: "copilot", label: "Copilot", hint: "Chat és telefon támogatás", path: "/copilot" },
  { id: "postal", label: "Postai levél", hint: "OCR workflow", path: "/postal" },
  { id: "eval", label: "Evaluation", hint: "Minőségmérés", path: "/eval" },
  { id: "knowledge", label: "ÁSZF tudásböngésző", hint: "/knowledge", path: "/knowledge" },
  { id: "supervisor", label: "Supervisor", hint: "Audit és operáció", path: "/supervisor", roles: ["supervisor"] },
];

export function CommandPalette({ role }: { role: Role }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => !value);
      }
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const commands = useMemo(() => {
    const folded = query.toLowerCase().trim();
    return commandRegistry
      .filter((item) => !item.roles || item.roles.includes(role))
      .filter((item) => !folded || `${item.label} ${item.hint}`.toLowerCase().includes(folded));
  }, [query, role]);

  const runCommand = (item: CommandItem) => {
    setOpen(false);
    setQuery("");
    if (location.pathname !== item.path) navigate(item.path);
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-4 right-4 z-30 bg-one-surface border border-one-line shadow-card rounded-pill px-3 py-1.5 text-[11px] text-one-grey hover:text-one-ink"
        aria-label="Command palette megnyitása"
      >
        Ctrl+K
      </button>
      {open && (
        <div className="fixed inset-0 z-40 bg-black/20 flex items-start justify-center pt-24" role="dialog" aria-modal="true" aria-label="Command palette">
          <div className="w-[520px] bg-one-surface border border-one-line rounded-one shadow-card overflow-hidden">
            <div className="border-b border-one-line p-3">
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Parancs keresése..."
                className="w-full bg-one-canvas border border-one-line rounded-md px-3 py-2 text-[13px] focus:outline-none focus:ring-2 focus:ring-one-turq"
                aria-label="Command palette keresés"
              />
            </div>
            <div className="max-h-80 overflow-auto divide-y divide-one-line">
              {commands.map((item) => (
                <button key={item.id} onClick={() => runCommand(item)} className="block w-full text-left px-3 py-2 hover:bg-one-canvas">
                  <div className="text-[12px] font-semibold text-one-ink">{item.label}</div>
                  <div className="text-[10px] text-one-grey">{item.hint}</div>
                </button>
              ))}
              {!commands.length && <p className="p-4 text-[12px] text-one-grey">Nincs találat.</p>}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
