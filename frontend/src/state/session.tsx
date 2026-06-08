import React, { createContext, useContext, useState, useCallback } from "react";
import type { User, ModelProfile, OutputMode } from "../lib/types";

interface SessionState {
  user: User | null;
  modelProfile: ModelProfile;
  outputMode: OutputMode;
  aszfVersion: string;
  login: (u: User) => void;
  logout: () => void;
  setModelProfile: (p: ModelProfile) => void;
  setOutputMode: (m: OutputMode) => void;
  setAszfVersion: (v: string) => void;
}

const CTX = createContext<SessionState | null>(null);

function load<T>(key: string, fallback: T): T {
  try {
    const v = localStorage.getItem(key);
    return v ? (JSON.parse(v) as T) : fallback;
  } catch {
    return fallback;
  }
}

function save(key: string, value: unknown) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch {}
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(() => load("session.user", null));
  const [modelProfile, setModelProfileState] = useState<ModelProfile>(() => load("session.modelProfile", "cloud"));
  const [outputMode, setOutputModeState] = useState<OutputMode>(() => load("session.outputMode", "hitl"));
  const [aszfVersion, setAszfVersionState] = useState("—");

  const login = useCallback((u: User) => {
    setUser(u);
    save("session.user", u);
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem("session.user");
  }, []);

  const setModelProfile = useCallback((p: ModelProfile) => {
    setModelProfileState(p);
    save("session.modelProfile", p);
  }, []);

  const setOutputMode = useCallback((m: OutputMode) => {
    setOutputModeState(m);
    save("session.outputMode", m);
  }, []);

  const setAszfVersion = useCallback((v: string) => {
    setAszfVersionState(v);
  }, []);

  return (
    <CTX.Provider value={{ user, modelProfile, outputMode, aszfVersion, login, logout, setModelProfile, setOutputMode, setAszfVersion }}>
      {children}
    </CTX.Provider>
  );
}

export function useSession() {
  const ctx = useContext(CTX);
  if (!ctx) throw new Error("useSession must be used within SessionProvider");
  return ctx;
}
