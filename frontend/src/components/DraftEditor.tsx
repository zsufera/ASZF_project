import { useEffect, useMemo, useRef, useState } from "react";
import type { DraftVersion, OutputMode } from "../lib/types";

interface DraftEditorProps {
  draft: { subject: string; body_masked: string; citations: string[] };
  versions: DraftVersion[];
  outputMode: OutputMode;
  caseId: string;
  onModeChange: (m: OutputMode) => void;
  onSave: (subject: string, body: string) => Promise<void>;
  onApprove: (subject: string, body: string, versionId: string) => Promise<void>;
  onFeedback: (rating: "jo" | "rossz", wrongSource?: boolean) => Promise<void>;
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

export function DraftEditor({ draft, versions, outputMode, onModeChange, onSave, onApprove, onFeedback, onCitationClick }: DraftEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [mode, setMode] = useState<"free" | "template">("free");
  const [subject, setSubject] = useState(draft.subject ?? "");
  const [body, setBody] = useState(draft.body_masked ?? "");
  const [selectedVersion, setSelectedVersion] = useState(versions[0]?.id ?? "");
  const [saving, setSaving] = useState(false);
  const [approving, setApproving] = useState(false);
  const [editMode, setEditMode] = useState(false);

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

  return (
    <div>
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <div className="flex border border-one-line rounded-md overflow-hidden text-[10px]">
          <button
            onClick={() => setMode("free")}
            className={`px-3 py-1 ${mode === "free" ? "bg-one-turq text-[#04201f] font-bold" : "text-one-grey hover:bg-one-canvas"}`}
          >
            Szabad szöveg
          </button>
          <button
            onClick={() => setMode("template")}
            className={`px-3 py-1 ${mode === "template" ? "bg-one-turq text-[#04201f] font-bold" : "text-one-grey hover:bg-one-canvas"}`}
          >
            Sablonblokkok
          </button>
        </div>

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

        <div className="ml-auto flex border border-one-line rounded-md overflow-hidden text-[10px]">
          <button
            onClick={() => onModeChange("hitl")}
            className={`px-3 py-1 ${outputMode === "hitl" ? "bg-one-turq text-[#04201f] font-bold" : "text-one-grey hover:bg-one-canvas"}`}
          >
            HITL
          </button>
          <button
            onClick={() => onModeChange("automata")}
            className={`px-3 py-1 ${outputMode === "automata" ? "bg-one-turq text-[#04201f] font-bold" : "text-one-grey hover:bg-one-canvas"}`}
          >
            Automata
          </button>
        </div>
      </div>

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

      <div className="grid grid-cols-3 gap-3 mb-3">
        <CitationInsertMenu citations={draft.citations} onInsert={insertCitation} onPreview={onCitationClick} />
        <ApprovalChecklist subject={subject} body={body} citations={draft.citations} selectedVersion={selectedVersion} />
        <DraftVersionDiff currentBody={body} previousBody={previousVersion?.body_masked ?? ""} previousLabel={previousVersion ? `v${previousVersion.version_no}` : "előző"} />
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={handleApprove}
          disabled={approving}
          className="bg-one-turq text-[#04201f] font-bold text-[11px] px-4 py-2 rounded-pill hover:bg-one-turq-d transition-colors disabled:opacity-50"
          aria-label="Jóváhagyom kiküldésre"
        >
          {approving ? "⏳ Jóváhagyás…" : "✓ Jóváhagyom kiküldésre"}
        </button>
        <button
          onClick={handleSave}
          disabled={saving}
          className="bg-white border border-one-line text-one-ink text-[11px] px-3 py-2 rounded-pill hover:bg-one-canvas transition-colors disabled:opacity-50"
          aria-label="Draft mentése"
        >
          {saving ? "…" : "💾 Draft mentése"}
        </button>
        <div className="ml-auto flex items-center gap-3 text-[12px] text-one-grey">
          <span>Visszajelzés:</span>
          <button onClick={() => onFeedback("jo")} className="hover:text-kpi-ok transition-colors" aria-label="Jó visszajelzés">👍</button>
          <button onClick={() => onFeedback("rossz")} className="hover:text-kpi-bad transition-colors" aria-label="Rossz visszajelzés">👎</button>
          <button onClick={() => onFeedback("rossz", true)} className="text-[10px] hover:text-kpi-bad transition-colors" aria-label="Rossz forrás">rossz forrás</button>
        </div>
      </div>
    </div>
  );
}

function CitationInsertMenu({
  citations,
  onInsert,
  onPreview,
}: {
  citations: string[];
  onInsert: (citation: string) => void;
  onPreview: (citation: string) => void;
}) {
  return (
    <div className="border border-one-line rounded-one bg-one-surface p-3">
      <div className="text-[10px] uppercase text-one-grey font-semibold tracking-wider mb-2">Citation beszúrás</div>
      {citations.length ? (
        <div className="flex flex-wrap gap-1">
          {citations.map((citation) => (
            <span key={citation} className="inline-flex rounded-full border border-one-line overflow-hidden">
              <button onClick={() => onInsert(citation)} className="px-2 py-1 text-[10px] bg-white hover:bg-one-canvas">{citation}</button>
              <button onClick={() => onPreview(citation)} className="px-2 py-1 text-[10px] bg-one-canvas text-one-grey hover:text-one-ink">forrás</button>
            </span>
          ))}
        </div>
      ) : (
        <p className="text-[11px] text-one-grey">Nincs beszúrható hivatkozás.</p>
      )}
    </div>
  );
}

function ApprovalChecklist({
  subject,
  body,
  citations,
  selectedVersion,
}: {
  subject: string;
  body: string;
  citations: string[];
  selectedVersion: string;
}) {
  const items = [
    { label: "Tárgy kitöltve", ok: subject.trim().length > 0 },
    { label: "Válaszszöveg kitöltve", ok: body.trim().length > 0 },
    { label: "Forráshivatkozás van", ok: citations.length > 0 },
    { label: "Draft verzió kiválasztva", ok: Boolean(selectedVersion) },
  ];
  return (
    <div className="border border-one-line rounded-one bg-one-surface p-3">
      <div className="text-[10px] uppercase text-one-grey font-semibold tracking-wider mb-2">Jóváhagyási checklist</div>
      <ul className="space-y-1">
        {items.map((item) => (
          <li key={item.label} className={item.ok ? "text-kpi-ok text-[11px]" : "text-status-urgent-fg text-[11px]"}>
            {item.ok ? "✓" : "!"} {item.label}
          </li>
        ))}
      </ul>
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
    <div className="border border-one-line rounded-one bg-one-surface p-3">
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
