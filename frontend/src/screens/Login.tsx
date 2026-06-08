import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSession } from "../state/session";
import { api } from "../lib/api";

export function Login() {
  const { login } = useSession();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.login(username, password);
      login({ username: res.username, role: res.role });
      navigate("/inbox");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bejelentkezési hiba");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-one-black flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 rounded-full border-2 border-one-turq text-one-turq italic font-extrabold text-2xl flex items-center justify-center mb-4">
            one
          </div>
          <h1 className="text-white font-bold text-xl text-center">ÁSZF Copilot</h1>
          <p className="text-[#9fb1af] text-[12px] mt-1">One Magyarország — Bejelentkezés</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-[#1a2625] rounded-one-lg p-6 flex flex-col gap-4">
          <div>
            <label htmlFor="username" className="text-[11px] text-[#9fb1af] block mb-1">Felhasználónév</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
              className="w-full bg-[#0e1212] border border-[#2a3c3a] rounded-md px-3 py-2 text-white text-[13px] focus:outline-none focus:ring-2 focus:ring-one-turq"
              placeholder="ui_demo"
            />
          </div>
          <div>
            <label htmlFor="password" className="text-[11px] text-[#9fb1af] block mb-1">Jelszó</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              className="w-full bg-[#0e1212] border border-[#2a3c3a] rounded-md px-3 py-2 text-white text-[13px] focus:outline-none focus:ring-2 focus:ring-one-turq"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div className="text-status-urgent-fg text-[12px] bg-status-urgent-bg rounded px-3 py-2" role="alert">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="bg-one-turq text-[#04201f] font-bold py-2.5 rounded-pill hover:bg-one-turq-d transition-colors disabled:opacity-50 text-[13px]"
          >
            {loading ? "Belépés…" : "Belépés"}
          </button>

          <p className="text-[#6b7a79] text-[10px] text-center">
            Demo: <code className="text-[#9fb1af]">ui_demo</code> / <code className="text-[#9fb1af]">ui_demo</code><br />
            vagy <code className="text-[#9fb1af]">supervisor_demo</code> / <code className="text-[#9fb1af]">supervisor_demo</code>
          </p>
        </form>
      </div>
    </div>
  );
}
