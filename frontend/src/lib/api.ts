import type {
  User, InboxItem, Case, HistoryItem, CustomerCandidateItem,
  EvalResult, EscalatedItem, SupervisorStats, OcrResult,
} from "./types";

const BASE = (import.meta.env.VITE_BACKEND_URL ?? "/api") as string;

async function req<T>(method: string, path: string, body?: unknown, formData?: FormData): Promise<T> {
  const opts: RequestInit = { method };
  if (formData) {
    opts.body = formData;
  } else if (body !== undefined) {
    opts.headers = { "Content-Type": "application/json" };
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${BASE}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error ?? err.detail ?? res.statusText);
  }
  const data = await res.json() as T & { error?: string };
  // A backend egyes végpontjai HTTP 200-zal adnak vissza { error: "..." }-t (pl. nem talált ügy)
  if ((data as { error?: string }).error) {
    throw new Error((data as { error?: string }).error);
  }
  return data;
}

export const api = {
  login: (username: string, password: string) =>
    req<User & { error?: string }>("POST", "/auth/login", { username, password }),

  health: () => req<{ aszf_version: string }>("GET", "/health"),

  getInbox: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return req<{ items: InboxItem[] }>("GET", `/inbox${qs}`);
  },

  getCase: (id: string) => req<Case>("GET", `/cases/${id}`),

  createCase: (body: { channel: string; input_text: string; sender_email?: string; service_provider?: string }) =>
    req<{ case_id: string }>("POST", "/cases/create", body),

  processCase: (body: { case_id: string; output_mode: string; username: string; service_provider?: string }) =>
    req<{ timeline: unknown[] }>("POST", "/cases/process", body),

  saveDraft: (body: { case_id: string; subject: string; body_masked: string; output_mode: string; citations: string[]; username: string }) =>
    req<Record<string, unknown>>("POST", "/cases/draft", body),

  approveCase: (body: { case_id: string; subject_masked: string; body_masked: string; username: string; role: string; draft_version_id: string }) =>
    req<{ subject_unmasked: string; body_unmasked: string }>("POST", "/cases/approve", body),

  sendFeedback: (body: { case_id: string; rating: string; wrong_source?: boolean; username: string }) =>
    req<Record<string, unknown>>("POST", "/cases/feedback", body),

  updateStatus: (body: Record<string, unknown>) =>
    req<Record<string, unknown>>("POST", "/cases/status", body),

  getHistory: (address: string, senderEmailKey?: string) => {
    const params = new URLSearchParams({ address });
    if (senderEmailKey) params.set("sender_email_key", senderEmailKey);
    return req<{ items: HistoryItem[]; is_repeated: boolean }>("GET", `/history?${params.toString()}`);
  },

  getCustomerLookup: (address: string) =>
    req<{ candidates: CustomerCandidateItem[] }>("GET", `/customer-lookup?address=${encodeURIComponent(address)}`),

  ocr: (caseId: string, file: File) => {
    const fd = new FormData();
    fd.append("case_id", caseId);
    fd.append("pdf_file", file);
    return req<OcrResult>("POST", "/ocr", undefined, fd);
  },

  agentRun: (body: Record<string, unknown>) =>
    req<{ timeline: unknown[] }>("POST", "/agent/run", body),

  runEval: (body: { limit: number; category?: string; service_provider?: string; include_edge: boolean }) =>
    req<EvalResult>("POST", "/eval/run", body),

  getEvalRun: (runId: string) => req<EvalResult>("GET", `/eval/runs/${runId}`),

  setHumanScore: (body: { run_id: string; email_id: string; score: number }) =>
    req<Record<string, unknown>>("POST", "/eval/human-score", body),

  evalBaseline: (body: { run_id: string }) =>
    req<Record<string, unknown>>("POST", "/eval/baseline", body),

  getSupervisorQueue: () => req<{ items: EscalatedItem[] }>("GET", "/supervisor/queue"),

  getSupervisorStats: () => req<SupervisorStats>("GET", "/supervisor/stats"),

  getAuditCase: (caseId: string, role: string) =>
    req<{ iterations: unknown[] }>("GET", `/audit/cases/${caseId}?role=${role}`),

  purgeGovernance: (body: { dry_run: boolean; username: string; role: string }) =>
    req<Record<string, unknown>>("POST", "/governance/purge", body),
};
