import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useToast } from "../state/toast";

export function NewCase() {
  const navigate = useNavigate();
  const { show } = useToast();
  const [channel, setChannel] = useState("email");
  const [inputText, setInputText] = useState("");
  const [senderEmail, setSenderEmail] = useState("");
  const [provider, setProvider] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) { setError("Az üzenet szövege kötelező."); return; }
    setLoading(true);
    setError("");
    try {
      const res = await api.createCase({ channel, input_text: inputText, sender_email: senderEmail || undefined, service_provider: provider || undefined });
      show("Ügy létrehozva!");
      navigate(`/case/${res.case_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Hiba");
    } finally {
      setLoading(false);
    }
  };

  const selectClass = "text-[12px] border border-one-line rounded-md px-2 py-1.5 bg-white w-full focus:outline-none focus:ring-2 focus:ring-one-turq";
  const inputClass = "text-[12px] border border-one-line rounded-md px-2 py-1.5 bg-white w-full focus:outline-none focus:ring-2 focus:ring-one-turq";

  return (
    <div className="max-w-xl">
      <h1 className="text-[16px] font-bold text-one-ink mb-4">Új ügy létrehozása</h1>
      <form onSubmit={handleSubmit} className="bg-one-surface border border-one-line rounded-one shadow-card p-5 flex flex-col gap-4">
        <div>
          <label className="text-[11px] text-one-grey block mb-1">Csatorna</label>
          <select value={channel} onChange={(e) => setChannel(e.target.value)} className={selectClass} aria-label="Csatorna">
            <option value="email">Email</option>
            <option value="chat">Chat</option>
            <option value="postal">Postai</option>
            <option value="telefon">Telefon</option>
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
        <div>
          <label className="text-[11px] text-one-grey block mb-1">Üzenet szövege</label>
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            required
            rows={6}
            className={`${inputClass} resize-y`}
            placeholder="Illessze be az ügyfél üzenetét…"
            aria-label="Üzenet szövege"
          />
        </div>
        {error && <div className="text-status-urgent-fg text-[12px]" role="alert">{error}</div>}
        <button
          type="submit"
          disabled={loading}
          className="bg-one-turq text-[#04201f] font-bold text-[12px] py-2.5 rounded-pill hover:bg-one-turq-d transition-colors disabled:opacity-50"
        >
          {loading ? "Létrehozás…" : "Ügy létrehozása"}
        </button>
      </form>
    </div>
  );
}
