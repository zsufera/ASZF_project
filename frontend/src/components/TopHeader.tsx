import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Cloud, Server, User, LogOut, AlertTriangle } from "lucide-react";
import type { ModelProfile } from "../lib/types";
import { useSession } from "../state/session";

interface TopHeaderProps {
  aszfVersion: string;
  modelProfile: ModelProfile;
  onProviderChange: (p: ModelProfile) => void;
  offline: boolean;
}

export function TopHeader({ aszfVersion, modelProfile, onProviderChange, offline }: TopHeaderProps) {
  const { user, logout } = useSession();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const q = search.trim();
    if (!q) return;
    if (/^\d+$/.test(q) || q.startsWith("CASE-") || q.startsWith("case-")) {
      navigate(`/case/${q}`);
    } else {
      navigate(`/inbox?search=${encodeURIComponent(q)}`);
    }
    setSearch("");
  };

  return (
    <header
      className="h-[52px] bg-one-surface border-b border-one-line flex items-center gap-3 px-4"
      style={{ zIndex: 10 }}
    >
      <div className="flex items-center gap-2 shrink-0">
        <div
          className="w-7 h-7 rounded-full border-2 border-one-turq text-one-turq italic font-bold text-[12px] flex items-center justify-center"
          aria-label="One logó"
        >
          one
        </div>
        <span className="font-bold text-[13px] text-one-ink hidden sm:block">ÁSZF Copilot</span>
      </div>

      <form onSubmit={handleSearch} className="flex-1 max-w-xs">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Ügy-azonosító / feladó…"
          className="w-full bg-[#F4F8F7] border border-one-line rounded-full px-3 py-1.5 text-[11px] text-one-grey focus:outline-none focus:ring-2 focus:ring-one-turq"
          aria-label="Globális keresés"
        />
      </form>

      <div className="flex items-center gap-2 ml-auto shrink-0">
        {offline && (
          <span className="text-status-esc-fg text-[10px] font-semibold hidden md:block flex items-center gap-1">
            <AlertTriangle size={12} className="inline" /> Offline
          </span>
        )}
        <span className="text-[11px] bg-[#F4F8F7] border border-one-line rounded-xl px-3 py-1 hidden md:block">
          ÁSZF {aszfVersion}
        </span>
        <button
          onClick={() => onProviderChange(modelProfile === "cloud" ? "onprem" : "cloud")}
          className="text-[11px] bg-[#F4F8F7] border border-one-line rounded-xl px-3 py-1 hover:bg-one-turq-l transition-colors"
          aria-label={`Modell profil: ${modelProfile === "cloud" ? "Felhő" : "On-prem"}`}
        >
          {modelProfile === "cloud"
            ? <><Cloud size={12} className="inline mr-1" />Felhő</>
            : <><Server size={12} className="inline mr-1" />On-prem</>}
        </button>
        {user && (
          <div className="flex items-center gap-2 text-[11px]">
            <span className="text-one-grey hidden md:block flex items-center gap-1">
              <User size={12} className="inline" /> {user.username} · {user.role}
            </span>
            <button
              onClick={logout}
              className="text-[10px] text-one-grey hover:text-one-ink border border-one-line rounded-full px-2 py-0.5 transition-colors flex items-center gap-1"
              aria-label="Kijelentkezés"
            >
              <LogOut size={10} className="inline" />Kilép
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
