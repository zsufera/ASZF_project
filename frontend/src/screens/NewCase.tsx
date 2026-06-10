import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, Mail, Upload } from "lucide-react";
import { api } from "../lib/api";
import type { OcrResult } from "../lib/types";
import { useToast } from "../state/toast";

type Mode = "text" | "postal";

export function NewCase() {
  const navigate = useNavigate();
  const { show } = useToast();

  const [mode, setMode] = useState<Mode>("text");
  const [error, setError] = useState("");

  // Szöveg mód
  const [channel, setChannel] = useState("email");
  const [inputText, setInputText] = useState("");
  const [senderEmail, setSenderEmail] = useState("");
  const [provider, setProvider] = useState("");
  const [loading, setLoading] = useState(false);

  // Postai mód
  const [file, setFile] = useState<File | null>(null);
  const [ocrResult, setOcrResult] = useState<OcrResult | null>(null);
  const [editedText, setEditedText] = useState("");
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) { setError("Az üzenet szövege kötelező."); return; }
    setLoading(true);
    setError("");
    try {
      const res = await api.createCase({ channel, input_text: inputText, sender_email: senderEmail || undefined, service_provider: provider || undefined });
      show("Ügy létrehozva!");
      navigate(`/case/${res.case_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Hiba");
    } finally {
      setLoading(false);
    }
  };

  const handleFile = (f: File) => {
    if (!f.name.toLowerCase().endsWith(".pdf")) { setError("Csak PDF fájl fogadható el."); return; }
    setFile(f);
    setError("");
    setOcrResult(null);
    setEditedText("");
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const res = await api.ocr("postal-" + Date.now(), file);
      setOcrResult(res);
      setEditedText(res.ocr_text_masked);
    } catch (err) {
      setError(err instanceof Error ? err.message : "OCR hiba");
    } finally {
      setUploading(false);
    }
  };

  const handlePostalProcess = async () => {
    setProcessing(true);
    setError("");
    try {
      const res = await api.createCase({ channel: "postal", input_text: editedText });
      show("Ügy létrehozva!");
      navigate(`/case/${res.case_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Hiba");
    } finally {
      setProcessing(false);
    }
  };

  const inputClass = "text-[12px] border border-one-line rounded-md px-2 py-1.5 bg-white w-full focus:outline-none focus:ring-2 focus:ring-one-turq";
  const confColor = ocrResult
    ? ocrResult.ocr_confidence > 0.85 ? "text-kpi-ok" : ocrResult.ocr_confidence > 0.6 ? "text-kpi-warn" : "text-kpi-bad"
    : "";

  return (
    <div className="max-w-5xl">
      <div className="mb-4">
        <h1 className="text-[16px] font-bold text-one-ink">Új ügy létrehozása</h1>
        <p className="text-[11px] text-one-grey">Illessz be egy ügyfélüzenetet, vagy tölts fel egy postai levelet (PDF) OCR-feldolgozásra.</p>
      </div>

      {/* Mód-választó */}
      <div className="inline-flex p-1 mb-4 bg-one-canvas border border-one-line rounded-pill">
        <ModeTab active={mode === "text"} onClick={() => setMode("text")} icon={<FileText size={14} />} label="Szöveg beillesztése" />
        <ModeTab active={mode === "postal"} onClick={() => setMode("postal")} icon={<Mail size={14} />} label="Postai levél (PDF)" />
      </div>

      {error && <div className="mb-3 text-status-urgent-fg text-[12px] bg-status-urgent-bg border border-status-urgent-fg rounded-md px-3 py-2" role="alert">{error}</div>}

      {mode === "text" ? (
        <form onSubmit={handleTextSubmit} className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4 items-start">
          <section className="bg-one-surface border border-one-line rounded-one shadow-card p-4 flex flex-col gap-3">
            <div className="text-[10px] uppercase tracking-wider text-one-grey font-semibold">Ügy adatai</div>
            <div>
              <label className="text-[11px] text-one-grey block mb-1">Csatorna</label>
              <select value={channel} onChange={(e) => setChannel(e.target.value)} className={inputClass} aria-label="Csatorna">
                <option value="email">Email</option>
                <option value="chat">Chat</option>
                <option value="telefon">Telefon</option>
                <option value="postal">Postai</option>
              </select>
            </div>
            <div>
              <label className="text-[11px] text-one-grey block mb-1">Feladó email (opcionális)</label>
              <input value={senderEmail} onChange={(e) => setSenderEmail(e.target.value)} type="email" className={inputClass} placeholder="ugyfel@example.com" aria-label="Feladó email" />
            </div>
            <div>
              <label className="text-[11px] text-one-grey block mb-1">Szolgáltató (opcionális)</label>
              <input value={provider} onChange={(e) => setProvider(e.target.value)} className={inputClass} placeholder="pl. One Magyarország" aria-label="Szolgáltató" />
            </div>
          </section>

          <section className="bg-one-surface border border-one-line rounded-one shadow-card p-4 flex flex-col gap-3">
            <div className="text-[10px] uppercase tracking-wider text-one-grey font-semibold">Üzenet szövege</div>
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              required
              rows={12}
              className={`${inputClass} resize-y flex-1 min-h-[260px]`}
              placeholder="Illessze be az ügyfél üzenetét…"
              aria-label="Üzenet szövege"
            />
            <button
              type="submit"
              disabled={loading}
              className="self-start bg-one-turq text-[#04201f] font-bold text-[12px] px-6 py-2.5 rounded-pill hover:bg-one-turq-d transition-colors disabled:opacity-50 btn-press"
            >
              {loading ? "Létrehozás…" : "Ügy létrehozása"}
            </button>
          </section>
        </form>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
          <section className="bg-one-surface border border-one-line rounded-one shadow-card p-4 flex flex-col gap-3">
            <div className="text-[10px] uppercase tracking-wider text-one-grey font-semibold">PDF feltöltés</div>
            <div
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
              className={`border-2 border-dashed rounded-one p-8 text-center cursor-pointer transition-colors ${dragging ? "border-one-turq bg-one-turq-l" : "border-one-line hover:border-one-turq bg-one-canvas"}`}
              role="button"
              aria-label="PDF feltöltés — kattints vagy húzd ide a fájlt"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === "Enter") inputRef.current?.click(); }}
            >
              <input ref={inputRef} type="file" accept=".pdf" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }} />
              <Upload size={28} className="mx-auto mb-2 text-one-grey" />
              <p className="text-one-grey text-[13px] mb-1">Húzd ide a PDF fájlt, vagy kattints a feltöltéshez</p>
              {file && <p className="text-one-turq-d font-semibold text-[12px] mt-1">{file.name}</p>}
            </div>
            {file && !ocrResult && (
              <button
                onClick={handleUpload}
                disabled={uploading}
                className="self-start bg-one-turq text-[#04201f] font-bold text-[12px] px-5 py-2 rounded-pill hover:bg-one-turq-d transition-colors disabled:opacity-50 btn-press"
              >
                {uploading ? "OCR feldolgozás…" : "OCR indítása"}
              </button>
            )}
            {ocrResult && (
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-one-grey">OCR konfidencia</span>
                <span className={`font-semibold ${confColor}`}>{(ocrResult.ocr_confidence * 100).toFixed(0)}%</span>
              </div>
            )}
            {ocrResult && ocrResult.ocr_confidence < 0.7 && (
              <div className="text-status-esc-fg text-[11px] bg-status-esc-bg rounded px-2 py-1">
                Alacsony OCR konfidencia — ellenőrizd a szöveget manuálisan.
              </div>
            )}
          </section>

          <section className="bg-one-surface border border-one-line rounded-one shadow-card p-4 flex flex-col gap-3">
            <div className="text-[10px] uppercase tracking-wider text-one-grey font-semibold">OCR szöveg</div>
            {ocrResult ? (
              <>
                <textarea
                  value={editedText}
                  onChange={(e) => setEditedText(e.target.value)}
                  rows={12}
                  className={`${inputClass} resize-y flex-1 min-h-[260px]`}
                  aria-label="OCR szöveg szerkesztése"
                />
                <button
                  onClick={handlePostalProcess}
                  disabled={processing || !editedText.trim()}
                  className="self-start bg-one-turq text-[#04201f] font-bold text-[12px] px-6 py-2.5 rounded-pill hover:bg-one-turq-d transition-colors disabled:opacity-50 btn-press"
                >
                  {processing ? "Feldolgozás…" : "Feldolgozás → Ügy"}
                </button>
              </>
            ) : (
              <div className="flex-1 min-h-[260px] flex items-center justify-center text-center text-one-grey text-[12px] border border-dashed border-one-line rounded-md">
                Tölts fel egy PDF-et és futtasd az OCR-t — a felismert szöveg itt jelenik meg szerkeszthetően.
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

function ModeTab({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 text-[12px] font-semibold px-4 py-1.5 rounded-pill transition-colors ${active ? "bg-one-turq text-[#04201f]" : "text-one-grey hover:text-one-ink"}`}
      aria-pressed={active}
    >
      {icon}
      {label}
    </button>
  );
}
