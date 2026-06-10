import { useEffect, useMemo, useRef, useState } from "react";
import { FEEDBACK_REASON_LABELS } from "../lib/feedbackReasons";
import type { DraftVersion, FeedbackReason } from "../lib/types";

interface DraftEditorProps {
  draft: { subject: string; body_masked: string; citations: string[] };
  versions: DraftVersion[];
  caseId: string;
  onSave: (subject: string, body: string) => Promise<void>;
  onApprove: (subject: string, body: string, versionId: string) => Promise<void>;
  onFeedback: (rating: "jo" | "rossz", reason?: FeedbackReason) => Promise<void>;
  onCitationClick: (citation: string) => void;
}

function renderBodyWithCitations(body: string, citations: string[], onClick: (c: string) => void) {
  if (!citations.length) return <span>{body}</span>;
  const parts: React.ReactNode[] = [];
  let remaining = body;
  citations.forEach((cit) => {
    const idx = remaining.indexOf(cit);
    if (idx === -1) return;
    parts.push(remaining.slice(0, idx));
    parts.push(
      <button
        key={cit}
        onClick={() => onClick(cit)}
        className="bg-one-turq-l text-one-turq-d rounded px-1 font-semibold text-[10px] hover:bg-one-turq/20 transition-colors"
        aria-label={`Forrás: ${cit}`}
      >
        {cit}
      </button>
    );
    remaining = remaining.slice(idx + cit.length);
  });
  parts.push(remaining);
  return <>{parts}</>;
}

export function DraftEditor({ draft, versions, onSave, onApprove, onFeedback, onCitationClick }: DraftEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [subject, setSubject] = useState(draft.subject ?? "");
  const [body, setBody] = useState(draft.body_masked ?? "");
  const [selectedVersion, setSelectedVersion] = useState(versions[0]?.id ?? "");
  const [saving, setSaving] = useState(false);
  const [reasonOpen, setReasonOpen] = useState(false);
  const [approving, setApproving] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [showDiff, setShowDiff] = useState(false);

  const selectedVersionRecord = useMemo(
    () => versions.find((x) => x.id === selectedVersion),
    [selectedVersion, versions],
  );
  const previousVersion = useMemo(() => {
    if (!selectedVersionRecord) return versions[1];
    return versions.find((v) => v.version_no === selectedVersionRecord.version_no - 1) ?? versions[1];
  }, [selectedVersionRecord, versions]);

  useEffect(() => {
    setSubject(draft.subject ?? "");
    setBody(draft.body_masked ?? "");
    setSelectedVersion(versions[0]?.id ?? "");
  }, [draft.subject, draft.body_masked, versions]);

  const handleSave = async () => {
    setSaving(true);
    try { await onSave(subject, body); } finally { setSaving(false); }
  };

  const handleApprove = async () => {
    setApproving(true);
    try { await onApprove(subject, body, selectedVersion); } finally { setApproving(false); }
  };

  const insertCitation = (citation: string) => {
    const token = citation.startsWith("[") ? citation : `[${citation}]`;
    const textarea = textareaRef.current;
    if (!textarea) {
      setBody((current) => `${current}${current.endsWith(" ") || !current ? "" : " "}${token}`);
      setEditMode(true);
      return;
    }
    const start = textarea.selectionStart ?? body.length;
    const end = textarea.selectionEnd ?? body.length;
    const next = `${body.slice(0, start)}${token}${body.slice(end)}`;
    setBody(next);
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + token.length, start + token.length);
    }, 0);
  };

  const approvalReady = subject.trim().length > 0 && body.trim().length > 0 && Boolean(selectedVersion);

  return (
    <div>
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        {versions.length > 0 && (
          <select
            value={selectedVersion}
            onChange={(e) => {
              setSelectedVersion(e.target.value);
              const v = versions.find((x) => x.id === e.target.value);
              if (v) { setSubject(v.subject); setBody(v.body_masked); }
            }}
            className="text-[10px] border border-one-line rounded-md px-2 py-1 text-one-grey bg-white"
            aria-label="Verziótörténet"
          >
            {versions.map((v) => (
              <option key={v.id} value={v.id}>v{v.version_no} — {v.created_at.slice(0, 10)}</option>
            ))}
          </select>
        )}
        {versions.length >= 2 && (
          <button
            onClick={() => setShowDiff((v) => !v)}
            className="text-[10px] text-one-turq-d hover:underline"
          >
            {showDiff ? "Diff elrejtése" : "Diff"}
          </button>
        )}
      </div>

      {showDiff && versions.length >= 2 && (
        <DraftVersionDiff
          currentBody={body}
          previousBody={previousVersion?.body_masked ?? ""}
          previousLabel={previousVersion ? `v${previousVersion.version_no}` : "előző"}
        />
      )}

      <div className="mb-2">
        <label className="text-[10px] text-one-grey block mb-1">Tárgy</label>
        <input
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          className="w-full border border-one-line rounded-md px-2 py-1.5 text-[12px] focus:outline-none focus:ring-2 focus:ring-one-turq"
          aria-label="Draft tárgy"
        />
      </div>

      <div className="border border-one-line rounded-md p-3 min-h-[120px] text-[12px] leading-relaxed bg-white mb-3">
        {editMode ? (
          <textarea
            ref={textareaRef}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            onBlur={() => setEditMode(false)}
            autoFocus
            className="w-full min-h-[100px] outline-none resize-none text-[12px] leading-relaxed"
            aria-label="Draft szöveg szerkesztése"
          />
        ) : (
          <div
            onClick={() => setEditMode(true)}
            className="cursor-text whitespace-pre-wrap"
            role="textbox"
            aria-label="Draft szöveg — kattints a szerkesztéshez"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === "Enter") setEditMode(true); }}
          >
            {renderBodyWithCitations(body, draft.citations, onCitationClick)}
          </div>
        )}
      </div>

      {draft.citations.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-1">
          <span className="text-[10px] text-one-grey mr-1 self-center">Hivatkozás-beszúrás:</span>
          {draft.citations.map((citation) => (
            <span key={citation} className="inline-flex rounded-full border border-one-line overflow-hidden">
              <button onClick={() => insertCitation(citation)} className="px-2 py-1 text-[10px] bg-white hover:bg-one-canvas">{citation}</button>
              <button onClick={() => onCitationClick(citation)} className="px-2 py-1 text-[10px] bg-one-canvas text-one-grey hover:text-one-ink">forrás</button>
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={handleApprove}
          disabled={approving || !approvalReady}
          title={!approvalReady ? "Tárgy, szöveg és verzió szükséges" : undefined}
          className="bg-one-turq text-[#04201f] font-bold text-[11px] px-4 py-2 rounded-pill hover:bg-one-turq-d transition-colors disabled:opacity-50 btn-press"
          aria-label="Jóváhagyom kiküldésre"
        >
          {approving ? "Jóváhagyás…" : "✓ Jóváhagyom kiküldésre"}
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="bg-white border border-one-line text-one-ink text-[11px] px-3 py-2 rounded-pill hover:bg-one-canvas transition-colors disabled:opacity-50"
          aria-label="Draft mentése"
        >
          {saving ? "…" : "Draft mentése"}
        </button>
        <div className="ml-auto flex items-center gap-3 text-[12px] text-one-grey relative">
          <span>Visszajelzés:</span>
          <button
            onClick={() => { setReasonOpen(false); onFeedback("jo"); }}
            className="hover:text-kpi-ok transition-colors"
            aria-label="Jó visszajelzés"
          >
            👍
          </button>
          <button
            onClick={() => setReasonOpen((v) => !v)}
            className="hover:text-kpi-bad transition-colors"
            aria-label="Rossz visszajelzés"
            aria-expanded={reasonOpen}
          >
            👎
          </button>
          {reasonOpen && (
            <div className="absolute bottom-7 right-0 z-10 bg-one-surface border border-one-line rounded-one shadow-card p-1 flex flex-col min-w-[180px]">
              <div className="text-[10px] text-one-grey px-2 py-1">Mi volt a probléma?</div>
              {(Object.entries(FEEDBACK_REASON_LABELS) as Array<[FeedbackReason, string]>).map(([code, label]) => (
                <button
                  key={code}
                  onClick={() => { setReasonOpen(false); onFeedback("rossz", code); }}
                  className="text-left text-[11px] px-2 py-1.5 rounded-md hover:bg-one-canvas transition-colors"
                >
                  {label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function DraftVersionDiff({
  currentBody,
  previousBody,
  previousLabel,
}: {
  currentBody: string;
  previousBody: string;
  previousLabel: string;
}) {
  const currentLines = currentBody.split("\n").filter((line) => line.trim());
  const previous = new Set(previousBody.split("\n").map((line) => line.trim()).filter(Boolean));
  const changed = currentLines.filter((line) => !previous.has(line.trim())).slice(0, 4);
  return (
    <div className="border border-one-line rounded-one bg-one-surface p-3 mb-3">
      <div className="text-[10px] uppercase text-one-grey font-semibold tracking-wider mb-2">Verzió-diff ({previousLabel})</div>
      {changed.length ? (
        <div className="space-y-1">
          {changed.map((line, index) => (
            <div key={`${line}-${index}`} className="rounded bg-[#eefaf4] text-kpi-ok text-[10px] px-2 py-1 line-clamp-2">+ {line}</div>
          ))}
        </div>
      ) : (
        <p className="text-[11px] text-one-grey">Nincs látható szöveges eltérés.</p>
      )}
    </div>
  );
}
