import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useToast } from "../state/toast";
import type { OcrResult } from "../lib/types";

export function Postal() {
  const navigate = useNavigate();
  const { show } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [ocrResult, setOcrResult] = useState<OcrResult | null>(null);
  const [editedText, setEditedText] = useState("");
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const TEMP_CASE_ID = "postal-" + Date.now();

  const handleFile = (f: File) => {
    if (!f.name.endsWith(".pdf")) { setError("Csak PDF fájl fogadható el."); return; }
    setFile(f);
    setError("");
    setOcrResult(null);
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
      const res = await api.ocr(TEMP_CASE_ID, file);
      setOcrResult(res);
      setEditedText(res.ocr_text_masked);
    } catch (e) {
      setError(e instanceof Error ? e.message : "OCR hiba");
    } finally {
      setUploading(false);
    }
  };

  const handleProcess = async () => {
    setProcessing(true);
    try {
      const res = await api.createCase({ channel: "postal", input_text: editedText });
      show("Ügy létrehozva!");
      navigate(`/case/${res.case_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Hiba");
    } finally {
      setProcessing(false);
    }
  };

  const confColor = ocrResult
    ? ocrResult.ocr_confidence > 0.85 ? "text-kpi-ok" : ocrResult.ocr_confidence > 0.6 ? "text-kpi-warn" : "text-kpi-bad"
    : "";

  return (
    <div className="max-w-xl">
      <h1 className="text-[16px] font-bold text-one-ink mb-4">Postai levél import</h1>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-one p-8 text-center cursor-pointer transition-colors mb-4 ${dragging ? "border-one-turq bg-one-turq-l" : "border-one-line hover:border-one-turq bg-one-surface"}`}
        role="button"
        aria-label="PDF feltöltés — kattints vagy húzd ide a fájlt"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === "Enter") inputRef.current?.click(); }}
      >
        <input ref={inputRef} type="file" accept=".pdf" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }} />
        <p className="text-one-grey text-[13px] mb-1">📮 Húzd ide a PDF fájlt, vagy kattints a feltöltéshez</p>
        {file && <p className="text-one-turq-d font-semibold text-[12px]">{file.name}</p>}
      </div>

      {file && !ocrResult && (
        <button
          onClick={handleUpload}
          disabled={uploading}
          className="bg-one-turq text-[#04201f] font-bold text-[12px] px-5 py-2 rounded-pill hover:bg-one-turq-d transition-colors disabled:opacity-50 mb-4"
        >
          {uploading ? "⟳ OCR feldolgozás…" : "OCR indítása"}
        </button>
      )}

      {error && <div className="text-status-urgent-fg text-[12px] mb-3" role="alert">{error}</div>}

      {ocrResult && (
        <div className="bg-one-surface border border-one-line rounded-one shadow-card p-4">
          <div className="flex items-center justify-between mb-2">
            <h2 className="font-semibold text-[13px]">OCR Előnézet</h2>
            <span className={`text-[11px] font-semibold ${confColor}`}>
              Konfidencia: {(ocrResult.ocr_confidence * 100).toFixed(0)}%
            </span>
          </div>
          {ocrResult.ocr_confidence < 0.7 && (
            <div className="text-status-esc-fg text-[11px] bg-status-esc-bg rounded px-2 py-1 mb-2">
              ⚠ Alacsony OCR konfidencia — ellenőrizze a szöveget manuálisan.
            </div>
          )}
          <textarea
            value={editedText}
            onChange={(e) => setEditedText(e.target.value)}
            rows={10}
            className="w-full border border-one-line rounded-md px-3 py-2 text-[12px] focus:outline-none focus:ring-2 focus:ring-one-turq resize-y mb-3"
            aria-label="OCR szöveg szerkesztése"
          />
          <button
            onClick={handleProcess}
            disabled={processing || !editedText.trim()}
            className="bg-one-turq text-[#04201f] font-bold text-[12px] px-5 py-2 rounded-pill hover:bg-one-turq-d transition-colors disabled:opacity-50"
          >
            {processing ? "⟳ Feldolgozás…" : "Feldolgozás → Ügy"}
          </button>
        </div>
      )}
    </div>
  );
}
