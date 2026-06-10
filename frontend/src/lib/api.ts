import type {
  User, InboxItem, Case, HistoryItem, CustomerCandidateItem,
  EvalResult, EscalatedItem, SupervisorStats, OcrResult, CopilotChatResponse,
  AuditCaseRecord, AuditCompleteness, AuditEvent, TraceEvent, AcceptanceResult,
  AgentStreamEvent, CaseAssignmentResult, CopilotSessionItem,
  AszfKnowledgeGroup, AszfKnowledgeItem, OperationalMetrics,
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

function parseSseBlock(block: string): AgentStreamEvent | null {
  const lines = block.split("\n").map((line) => line.trimEnd()).filter(Boolean);
  const event = lines.find((line) => line.startsWith("event:"))?.slice("event:".length).trim() ?? "message";
  const dataLine = lines.find((line) => line.startsWith("data:"));
  if (!dataLine) return null;
  try {
    return { event, data: JSON.parse(dataLine.slice("data:".length).trim()) as Record<string, unknown> };
  } catch {
    return { event, data: { raw: dataLine.slice("data:".length).trim() } };
  }
}

async function streamPost(path: string, body: unknown, onEvent: (event: AgentStreamEvent) => void): Promise<void> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error ?? err.detail ?? res.statusText);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    const blocks = buffer.split(/\n\n/);
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      const event = parseSseBlock(block);
      if (event) onEvent(event);
    }
    if (done) break;
  }
  const trailing = parseSseBlock(buffer);
  if (trailing) onEvent(trailing);
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

  sendFeedback: (body: { case_id: string; rating: string; reason?: string; wrong_source?: boolean; username: string }) =>
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

  streamAgentRun: (body: Record<string, unknown>, onEvent: (event: AgentStreamEvent) => void) =>
    streamPost("/agent/run/stream", body, onEvent),

  copilotChat: (body: { session_id: string; message: string; history: { role: string; content: string }[]; customer_facing?: boolean }) =>
    req<CopilotChatResponse>("POST", "/copilot/chat", body),

  getCopilotSessions: (username?: string) => {
    const qs = username ? `?${new URLSearchParams({ username }).toString()}` : "";
    return req<{ items: CopilotSessionItem[]; count: number }>("GET", `/copilot/sessions${qs}`);
  },

  recordCopilotTurn: (body: { session_id: string; role: string; content: string; username?: string; sources?: unknown[]; timeline?: unknown[] }) =>
    req<Record<string, unknown>>("POST", "/copilot/sessions/turn", body),

  handoffCopilotSession: (body: { session_id: string; username?: string; selected_turn_ids?: number[] }) =>
    req<{ case_id: string; session_id: string; turn_count: number }>("POST", "/copilot/sessions/handoff", body),

  runEval: (body: { limit: number; category?: string; service_provider?: string; include_edge: boolean }) =>
    req<EvalResult>("POST", "/eval/run", body),

  getEvalRun: (runId: string) => req<EvalResult>("GET", `/eval/runs/${runId}`),

  setHumanScore: (body: { run_id: string; email_id: string; score: number }) =>
    req<Record<string, unknown>>("POST", "/eval/human-score", body),

  evalBaseline: (body: { run_id: string }) =>
    req<Record<string, unknown>>("POST", "/eval/baseline", body),

  runAcceptance: (body: { eval_limit: number; include_edge: boolean; run_demo: boolean }) =>
    req<AcceptanceResult>("POST", "/acceptance/run", body),

  getSupervisorQueue: () => req<{ items: EscalatedItem[] }>("GET", "/supervisor/queue"),

  getSupervisorStats: () => req<SupervisorStats>("GET", "/supervisor/stats"),

  getOperationalMetrics: () => req<OperationalMetrics>("GET", "/metrics/operational"),

  claimCase: (body: { case_id: string; username: string }) =>
    req<CaseAssignmentResult>("POST", "/cases/claim", body),

  assignCase: (body: { case_id: string; assignee_username: string; username: string }) =>
    req<CaseAssignmentResult>("POST", "/cases/assign", body),

  releaseCase: (body: { case_id: string; username: string }) =>
    req<CaseAssignmentResult>("POST", "/cases/release", body),

  getAuditCase: (caseId: string, role: string) =>
    req<AuditCaseRecord>("GET", `/audit/cases/${caseId}?role=${role}`),

  getAuditEvents: (params: { role: string; case_id?: string; limit?: number }) => {
    const qs = new URLSearchParams({ role: params.role });
    if (params.case_id) qs.set("case_id", params.case_id);
    if (params.limit) qs.set("limit", String(params.limit));
    return req<{ events: AuditEvent[]; count: number }>("GET", `/audit/events?${qs.toString()}`);
  },

  getAuditCompleteness: (caseId: string, role: string) =>
    req<AuditCompleteness>("GET", `/audit/completeness/${caseId}?role=${role}`),

  getTraces: (limit = 50) =>
    req<{ traces: TraceEvent[]; count: number }>("GET", `/observability/traces?limit=${limit}`),

  getAszfTree: () =>
    req<{ items: AszfKnowledgeGroup[]; count: number }>("GET", "/aszf/tree"),

  getAszfSection: (chunkId: string) =>
    req<{ item: AszfKnowledgeItem }>("GET", `/aszf/section/${encodeURIComponent(chunkId)}`),

  searchAszf: (q: string) =>
    req<{ items: AszfKnowledgeItem[]; count: number }>("GET", `/aszf/search?${new URLSearchParams({ q }).toString()}`),

  purgeGovernance: (body: { dry_run: boolean; username: string; role: string }) =>
    req<Record<string, unknown>>("POST", "/governance/purge", body),
};
