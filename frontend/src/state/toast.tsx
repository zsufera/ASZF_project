import React, { createContext, useContext, useState, useCallback } from "react";

interface Toast {
  id: number;
  message: string;
  kind: "success" | "error" | "info";
}

interface ToastCtx {
  toasts: Toast[];
  show: (message: string, kind?: Toast["kind"]) => void;
}

const CTX = createContext<ToastCtx | null>(null);
let _id = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const show = useCallback((message: string, kind: Toast["kind"] = "success") => {
    const id = ++_id;
    setToasts((prev) => [...prev, { id, message, kind }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3500);
  }, []);

  return (
    <CTX.Provider value={{ toasts, show }}>
      {children}
    </CTX.Provider>
  );
}

export function useToast() {
  const ctx = useContext(CTX);
  if (!ctx) throw new Error("useToast must be within ToastProvider");
  return ctx;
}
