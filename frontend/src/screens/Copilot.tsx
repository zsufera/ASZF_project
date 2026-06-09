import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useSession } from "../state/session";
import { useToast } from "../state/toast";
import { ChatTurn } from "../components/ChatTurn";
import type { GenerationMode, SourceRef } from "../lib/types";
import { InlineAnswer } from "../components/InlineAnswer";
import { RichSourceCard } from "../components/SourceCard";
import { ProcessingIndicator } from "../components/ProcessingIndicator";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: SourceRef[];
  generationMode?: GenerationMode;
}

const STREAMING_DELAY = 40;

function useStreamText(full: string, trigger: number) {
  const [displayed, setDisplayed] = useState("");
  useEffect(() => {
    if (!full) { setDisplayed(""); return; }
    setDisplayed("");
    let i = 0;
    const lines = full.split("\n");
    const interval = setInterval(() => {
      i++;
      setDisplayed(lines.slice(0, i).join("\n"));
      if (i >= lines.length) clearInterval(interval);
    }, STREAMING_DELAY);
    return () => clearInterval(interval);
  }, [full, trigger]);
  return displayed;
}

export function Copilot() {
  const navigate = useNavigate();
  const { user, outputMode } = useSession();
  const { show } = useToast();
  const [tab, setTab] = useState<"chat" | "telefon">("chat");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [createdCaseId, setCreatedCaseId] = useState<string | null>(() => {
    return sessionStorage.getItem("copilot.caseId");
  });
  // Ideiglenes case_id a chat-munkamenethez (az /agent/run kötelező mezője)
  const [sessionCaseId] = useState(() => `CHAT-${crypto.randomUUID()}`);
  const [transcript, setTranscript] = useState("");
  const [streamTrigger, setStreamTrigger] = useState(0);
  const [lastAssistantFull, setLastAssistantFull] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const streamedText = useStreamText(lastAssistantFull, streamTrigger);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamedText]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;
    const userMsg: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.agentRun({
        case_id: sessionCaseId,
        channel: "chat",
        input_text: text,
        output_mode: outputMode,
      }) as { draft?: { body_masked?: string; sources?: SourceRef[]; generation_mode?: GenerationMode } };

      const body = res.draft?.body_masked ?? "Nincs válasz.";
      const sources = res.draft?.sources ?? [];
      const generationMode = res.draft?.generation_mode;
      setLastAssistantFull(body);
      setStreamTrigger((n) => n + 1);
      setMessages((prev) => [...prev, { role: "assistant", content: body, sources, generationMode }]);
    } catch (e) {
      setMessages((prev) => [...prev, { role: "assistant", content: `Hiba: ${e instanceof Error ? e.message : "ismeretlen"}` }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const handleCreateCase = async () => {
    if (createdCaseId) { navigate(`/case/${createdCaseId}`); return; }
    const fullText = messages.map((m) => `${m.role === "user" ? "Ügyintéző" : "Copilot"}: ${m.content}`).join("\n");
    try {
      const res = await api.createCase({ channel: "chat", input_text: fullText });
      setCreatedCaseId(res.case_id);
      sessionStorage.setItem("copilot.caseId", res.case_id);
      show("Ügy létrehozva!");
      navigate(`/case/${res.case_id}`);
    } catch (e) {
      show(e instanceof Error ? e.message : "Hiba", "error");
    }
  };

  const handleTranscript = async () => {
    if (!transcript.trim()) return;
    sendMessage(transcript);
    setTranscript("");
  };

  return (
    <div>
      <h1 className="text-[16px] font-bold text-one-ink mb-3">Copilot</h1>

      <div className="flex gap-2 mb-4 border-b border-one-line">
        {(["chat", "telefon"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-[12px] rounded-t-lg border-b-2 transition-colors ${tab === t ? "border-one-turq text-one-turq-d font-bold bg-white" : "border-transparent text-one-grey hover:text-one-ink"}`}
            aria-selected={tab === t}
            role="tab"
          >
            {t === "chat" ? "💬 Chat" : "📞 Telefon"}
          </button>
        ))}
      </div>

      {tab === "chat" && (
        <div className="flex gap-3">
          <div className="flex-1 bg-one-surface border border-one-line rounded-one shadow-card flex flex-col" style={{ minHeight: "420px" }}>
            <div className="flex-1 p-4 overflow-y-auto">
              {messages.length === 0 && (
                <p className="text-one-grey text-[12px] text-center pt-8">Írj üzenetet a copilotnak…</p>
              )}
              {messages.map((m, i) => {
                const isLastAssistant = m.role === "assistant" && i === messages.length - 1;
                const streaming = isLastAssistant && loading;
                if (m.role === "assistant" && !streaming) {
                  return (
                    <div key={i} className="flex gap-2 mb-3 animate-fade-up">
                      <div className="w-7 h-7 rounded-full bg-one-turq-l flex items-center justify-center text-[11px] flex-none" aria-label="Copilot">◎</div>
                      <div className="rounded-xl px-3 py-2 max-w-[80%] bg-one-turq-l text-one-ink">
                        {m.generationMode === "insufficient" && (
                          <div className="mb-2 bg-status-esc-bg border border-status-esc-fg rounded-md px-2 py-1 text-[10px] text-status-esc-fg">
                            ⚠ Nincs elég ÁSZF-fedezet — emberi ellenőrzés / eszkaláció javasolt.
                          </div>
                        )}
                        <InlineAnswer body={m.content} sources={m.sources} onCite={(ref) => {
                          document.getElementById(`copilot-src-${ref}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
                        }} />
                      </div>
                    </div>
                  );
                }
                return (
                  <ChatTurn
                    key={i}
                    role={m.role}
                    content={streaming ? streamedText : m.content}
                  />
                );
              })}
              {loading && messages[messages.length - 1]?.role === "user" && (
                <div className="mb-3 animate-fade-up">
                  <ProcessingIndicator active={loading} />
                </div>
              )}
              <div ref={bottomRef} />
            </div>
            <div className="border-t border-one-line p-3 flex gap-2 items-end">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={2}
                placeholder="Írj üzenetet, vagy illeszd be a hívásátiratot… (Enter = küldés, Shift+Enter = új sor)"
                className="flex-1 bg-[#F4F8F7] border border-one-line rounded-xl px-3 py-2 text-[11px] focus:outline-none focus:ring-2 focus:ring-one-turq resize-none"
                aria-label="Üzenet"
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={loading || !input.trim()}
                className="bg-one-turq text-[#04201f] font-bold text-[11px] px-4 py-2 rounded-pill hover:bg-one-turq-d transition-colors disabled:opacity-50"
                aria-label="Küldés"
              >
                Küldés ➤
              </button>
            </div>
          </div>

          <div className="w-56 flex flex-col gap-3">
            {messages.length > 0 && (
              <div className="bg-one-surface border border-one-line rounded-one shadow-card p-3 text-[11px]">
                <h3 className="text-[10px] uppercase text-one-grey tracking-wider mb-2">↗ Ügy létrehozása</h3>
                <p className="text-one-grey mb-2">A jelenlegi beszélgetésből ügy nyitható.</p>
                <button
                  onClick={handleCreateCase}
                  className="bg-one-turq text-[#04201f] font-bold text-[10px] px-3 py-1.5 rounded-pill hover:bg-one-turq-d transition-colors w-full"
                >
                  {createdCaseId ? "Ügy megtekintése →" : "↗ Ügy létrehozása"}
                </button>
              </div>
            )}
            {(() => {
              const lastWithSources = [...messages].reverse().find((m) => m.sources && m.sources.length > 0);
              if (!lastWithSources?.sources?.length) return null;
              return (
                <div className="bg-one-surface border border-one-line rounded-one shadow-card p-3">
                  <h3 className="text-[10px] uppercase text-one-grey tracking-wider mb-2">📚 Hivatkozott források</h3>
                  {lastWithSources.sources.map((s) => (
                    <RichSourceCard key={s.ref} source={s} id={`copilot-src-${s.ref}`} />
                  ))}
                </div>
              );
            })()}
          </div>
        </div>
      )}

      {tab === "telefon" && (
        <div className="max-w-xl">
          <div className="bg-one-surface border border-one-line rounded-one shadow-card p-5">
            <h2 className="text-[13px] font-semibold mb-2">📞 Telefon-copilot</h2>
            <p className="text-one-grey text-[12px] mb-3">Illessze be a hívásátiratot, és az agent azonnal beszédpontokat ad.</p>
            <textarea
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              rows={8}
              placeholder="Hívásátirat szövege…"
              className="w-full border border-one-line rounded-md px-3 py-2 text-[12px] focus:outline-none focus:ring-2 focus:ring-one-turq resize-y mb-3"
              aria-label="Hívásátirat"
            />
            <button
              onClick={handleTranscript}
              disabled={loading || !transcript.trim()}
              className="bg-one-turq text-[#04201f] font-bold text-[12px] px-5 py-2 rounded-pill hover:bg-one-turq-d transition-colors disabled:opacity-50"
            >
              {loading ? "⟳ Feldolgozás…" : "Beszédpontok generálása"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
