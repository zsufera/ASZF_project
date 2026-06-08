interface SourceChipProps {
  label: string;
  onJump?: () => void;
}

export function SourceChip({ label, onJump }: SourceChipProps) {
  return (
    <button
      onClick={onJump}
      className="inline-flex items-center gap-1 text-[9px] bg-white border border-one-turq text-one-turq-d rounded-full px-2 py-0.5 font-semibold hover:bg-one-turq-l transition-colors"
      aria-label={`Forrás: ${label}`}
    >
      {label} ⤴
    </button>
  );
}

interface ChatTurnProps {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
}

export function ChatTurn({ role, content, sources }: ChatTurnProps) {
  const isUser = role === "user";
  return (
    <div className={`flex gap-2 mb-3 animate-fade-up ${isUser ? "justify-end" : ""}`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-one-turq-l flex items-center justify-center text-[11px] flex-none" aria-label="Copilot">◎</div>
      )}
      <div className={`rounded-xl px-3 py-2 text-[11px] leading-relaxed max-w-[80%] ${isUser ? "bg-[#F2F6F5] text-one-ink" : "bg-one-turq-l text-one-ink"}`}>
        {content}
        {sources && sources.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {sources.map((s, i) => <SourceChip key={i} label={s} />)}
          </div>
        )}
      </div>
      {isUser && (
        <div className="w-7 h-7 rounded-full bg-[#eef3f2] flex items-center justify-center text-[11px] flex-none" aria-label="Ügyintéző">🧑</div>
      )}
    </div>
  );
}
