import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import type { Case, OutputMode } from "../lib/types";
import { useSession } from "../state/session";
import { useToast } from "../state/toast";
import { Badge } from "../components/Badge";
import { Card } from "../components/Card";
import { SourceCard, RichSourceCard } from "../components/SourceCard";
import { InlineAnswer } from "../components/InlineAnswer";
import { ProcessingIndicator } from "../components/ProcessingIndicator";
import { HistoryCard } from "../components/HistoryCard";
import { CustomerCandidateList } from "../components/CustomerCandidate";
import { AgentTimeline } from "../components/AgentTimeline";
import { DraftEditor } from "../components/DraftEditor";
import { Modal } from "../components/Modal";

export function CaseWorkstation() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user, outputMode, setOutputMode } = useSession();
  const { show } = useToast();

  const [caseData, setCaseData] = useState<Case | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [processing, setProcessing] = useState(false);
  const [timelineOpen, setTimelineOpen] = useState(true);
  const [selectedCustomer, setSelectedCustomer] = useState<string | null>(null);
  const [history, setHistory] = useState<{ items: import("../lib/types").HistoryItem[]; is_repeated: boolean } | null>(null);
  const [approvalResult, setApprovalResult] = useState<{ subject_unmasked: string; body_unmasked: string } | null>(null);
  const sourceRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const fetchCase = useCallback(() => {
    if (!id) return;
    setLoading(true);
    api.getCase(id)
      .then((c) => {
        setCaseData(c);
        setError("");
        api.getHistory(c.sender_email_masked).then(setHistory).catch(() => {});
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => { fetchCase(); }, [fetchCase]);

  const handleProcess = async () => {
    if (!caseData || !user) return;
    setProcessing(true);
    try {
      await api.processCase({ case_id: caseData.case_id, output_mode: outputMode, username: user.username });
      fetchCase();
    } catch (e) {
      show(e instanceof Error ? e.message : "Hiba a feldolgozás során", "error");
    } finally {
      setProcessing(false);
    }
  };

  const handleSave = async (subject: string, body: string) => {
    if (!caseData || !user) return;
    await api.saveDraft({ case_id: caseData.case_id, subject, body_masked: body, output_mode: outputMode, citations: caseData.agent_state.draft?.citations ?? [], username: user.username });
    show("Draft mentve");
    fetchCase();
  };

  const handleApprove = async (subject: string, body: string, versionId: string) => {
    if (!caseData || !user) return;
    const res = await api.approveCase({ case_id: caseData.case_id, subject_masked: subject, body_masked: body, username: user.username, role: user.role, draft_version_id: versionId });
    setApprovalResult(res);
  };

  const handleFeedback = async (rating: "jo" | "rossz", wrongSource?: boolean) => {
    if (!caseData || !user) return;
    await api.sendFeedback({ case_id: caseData.case_id, rating, wrong_source: wrongSource, username: user.username });
    show(rating === "jo" ? "Köszönjük a visszajelzést! 👍" : "Visszajelzés elküldve");
  };

  const handleCitationClick = (citation: string) => {
    const chunks = caseData?.agent_state.retrieval.chunks ?? [];
    const match = chunks.find((c) => c.paragrafus.includes(citation) || citation.includes(c.paragrafus));
    if (match) {
      const ref = sourceRefs.current[match.chunk_id];
      if (ref) {
        ref.scrollIntoView({ behavior: "smooth", block: "center" });
        ref.classList.add("ring-2", "ring-one-turq");
        setTimeout(() => ref.classList.remove("ring-2", "ring-one-turq"), 1500);
      }
    }
  };

  const cols = timelineOpen ? "grid-cols-case-open" : "grid-cols-case-closed";

  if (loading) return <div className="text-one-grey p-8 text-center">Betöltés…</div>;
  if (error) return <div className="text-status-urgent-fg p-8">{error}</div>;
  if (!caseData) return null;

  const draft = caseData.agent_state?.draft ?? { subject: "", body_masked: "", citations: [] };
  const hasTimeline = (caseData.agent_state?.timeline ?? []).length > 0;
  const escalation = caseData.agent_state?.escalation ?? null;
  const chunks = caseData.agent_state?.retrieval?.chunks ?? [];
  const sources = caseData.agent_state?.draft?.sources ?? [];
  const generationMode = caseData.agent_state?.draft?.generation_mode;

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <button
          onClick={() => navigate("/inbox")}
          className="text-one-turq-d font-semibold text-[12px] hover:underline"
          aria-label="Vissza az inboxhoz"
        >
          ← Vissza az inboxhoz
        </button>
      </div>

      {/* Case header */}
      <div className="bg-gradient-to-r from-one-turq-l to-white border border-one-line rounded-one p-3 mb-4 flex flex-wrap items-center gap-2">
        <span className="font-bold text-[15px]">Ügy #{caseData.case_id}</span>
        <Badge kind="category" value={caseData.category_label} />
        {caseData.priority === "surgos" && <Badge kind="priority" value="SÜRGŐS" />}
        {caseData.escalated && <Badge kind="escalation" value="Eszkalált" />}
        {caseData.confidence < 0.7 && <Badge kind="confidence" value={caseData.confidence} />}
        <span className="ml-auto text-one-grey text-[11px]">📧 {caseData.sender_email_masked}</span>
        <span className="bg-white border border-one-line rounded-lg px-2 py-0.5 text-[11px] font-semibold">⏱ SLA: {caseData.sla_days_remaining} nap</span>
      </div>

      {/* Three columns */}
      <div className={`grid gap-3 transition-all duration-200 ${cols}`}>
        {/* LEFT: Context */}
        <div className="flex flex-col gap-3 min-w-0">
          <Card title="📚 Források">
            {sources.length > 0 ? (
              sources.map((s) => (
                <div key={s.ref} ref={(el) => { sourceRefs.current[s.ref] = el; }}>
                  <RichSourceCard source={s} id={`source-${s.ref}`} />
                </div>
              ))
            ) : chunks.length === 0 ? (
              <p className="text-one-grey text-[11px]">Nincs forrás.</p>
            ) : (
              chunks.map((c) => (
                <div key={c.chunk_id} ref={(el) => { sourceRefs.current[c.chunk_id] = el; }}>
                  <SourceCard chunk={c} id={`source-${c.chunk_id}`} />
                </div>
              ))
            )}
          </Card>

          <Card title="🕓 Előzmények">
            <HistoryCard
              items={history?.items ?? []}
              isRepeated={history?.is_repeated ?? false}
            />
          </Card>

          <Card title="👥 Ügyféltörzs-jelöltek">
            <CustomerCandidateList
              candidates={caseData.customer_candidates}
              selected={selectedCustomer}
              onSelect={setSelectedCustomer}
            />
          </Card>
        </div>

        {/* MIDDLE: Content + Draft */}
        <div className="flex flex-col gap-3 min-w-0">
          <Card title="✉️ Bejövő üzenet">
            <div className="text-[12px] leading-relaxed bg-[#FbFdfd] border border-one-line rounded-md p-3"
              dangerouslySetInnerHTML={{ __html: caseData.inbound_text_masked.replace(/\n/g, "<br>") }}
            />
          </Card>

          <Card title="✏️ Draft">
            {hasTimeline && (
              <div className="flex justify-end mb-2">
                <button
                  onClick={handleProcess}
                  disabled={processing}
                  className="text-[10px] text-one-turq-d border border-one-turq rounded-pill px-3 py-1 hover:bg-one-turq-l transition-colors disabled:opacity-50"
                  aria-label="Agent feldolgozás újrafuttatása"
                >
                  {processing ? "⟳ Feldolgozás…" : "🔄 Feldolgozás újra"}
                </button>
              </div>
            )}

            {escalation?.required && (
              <div className="mb-3 bg-status-esc-bg border border-status-esc-fg rounded-md p-2 text-[11px] text-status-esc-fg">
                ⚠ Eszkaláció supervisorhoz szükséges: {escalation.reasons.join(", ")}
              </div>
            )}

            {generationMode === "insufficient" && !processing && (
              <div className="mb-3 bg-status-esc-bg border border-status-esc-fg rounded-md p-2 text-[11px] text-status-esc-fg">
                ⚠ Nincs elég ÁSZF-fedezet automatikus válaszhoz — emberi ellenőrzés / eszkaláció javasolt.
              </div>
            )}

            {processing ? (
              <ProcessingIndicator active={processing} />
            ) : !hasTimeline ? (
              <div className="text-center py-6">
                <p className="text-one-grey text-[12px] mb-3">Az agent még nem futott.</p>
                <button
                  onClick={handleProcess}
                  disabled={processing}
                  className="bg-one-turq text-[#04201f] font-bold text-[12px] px-5 py-2 rounded-pill hover:bg-one-turq-d transition-colors disabled:opacity-50"
                >
                  ▶ Agent feldolgozás indítása
                </button>
              </div>
            ) : (
              <>
                {draft.body_masked && (
                  <div className="mb-3 bg-[#FbFdfd] border border-one-line rounded-md p-2">
                    <div className="text-[9px] uppercase text-one-grey tracking-wider mb-1">Fedezet-előnézet (kattintható forrás-jelölők)</div>
                    <InlineAnswer
                      body={draft.body_masked}
                      sources={sources}
                      onCite={(ref) => {
                        const el = sourceRefs.current[ref];
                        if (el) {
                          el.scrollIntoView({ behavior: "smooth", block: "center" });
                          el.classList.add("ring-2", "ring-one-turq");
                          setTimeout(() => el.classList.remove("ring-2", "ring-one-turq"), 1500);
                        }
                      }}
                    />
                  </div>
                )}
                <DraftEditor
                  draft={draft}
                  versions={caseData.draft_versions}
                  outputMode={outputMode}
                  caseId={caseData.case_id}
                  onModeChange={(m: OutputMode) => setOutputMode(m)}
                  onSave={handleSave}
                  onApprove={handleApprove}
                  onFeedback={handleFeedback}
                  onCitationClick={handleCitationClick}
                />
              </>
            )}
          </Card>
        </div>

        {/* RIGHT: Agent timeline */}
        <div className="min-w-0">
          {!hasTimeline ? (
            <div className="bg-one-surface border border-one-line rounded-one p-3 text-[11px] text-one-grey">
              Az idővonal az agent futása után jelenik meg.
            </div>
          ) : (
            <AgentTimeline
              steps={caseData.agent_state?.timeline ?? []}
              defaultOpen={true}
              onToggle={setTimelineOpen}
            />
          )}
          {escalation?.required && hasTimeline && (
            <div className="mt-3 bg-status-esc-bg border border-status-esc-fg rounded-one p-3 text-[11px]">
              <p className="font-semibold text-status-esc-fg mb-2">⚠ Eszkaláció szükséges</p>
              <button className="bg-status-esc-fg text-white text-[10px] px-3 py-1.5 rounded-pill font-bold hover:opacity-90 transition-opacity">
                ⚠ Eszkaláció supervisorhoz →
              </button>
            </div>
          )}
        </div>
      </div>

      {approvalResult && (
        <Modal title="Jóváhagyott tartalom — Küldésre kész" onClose={() => setApprovalResult(null)}>
          <div className="text-[12px] space-y-3">
            <div>
              <label className="text-one-grey text-[10px] uppercase">Tárgy</label>
              <p className="font-semibold mt-0.5">{approvalResult.subject_unmasked}</p>
            </div>
            <div>
              <label className="text-one-grey text-[10px] uppercase">Üzenet</label>
              <pre className="mt-0.5 whitespace-pre-wrap text-[11px] bg-one-canvas border border-one-line rounded p-2">{approvalResult.body_unmasked}</pre>
            </div>
            <button
              onClick={() => { show("Levél kiküldve!"); setApprovalResult(null); }}
              className="bg-one-turq text-[#04201f] font-bold text-[11px] px-4 py-2 rounded-pill hover:bg-one-turq-d transition-colors w-full"
            >
              ✓ Küldés megerősítése
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
