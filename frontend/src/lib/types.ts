export type Role = "ui" | "supervisor";
export type Priority = "surgos" | "normal";
export type KpiStatus = "green" | "yellow" | "red";
export type OutputMode = "hitl" | "automata";
export type ModelProfile = "cloud" | "onprem";
export type FeedbackRating = "jo" | "rossz";

export interface User {
  username: string;
  role: Role;
}

export interface InboxItem {
  case_id: string;
  category_label: string;
  priority: Priority;
  status_label: string;
  channel_label: string;
  subject: string;
  sla_days_remaining: number;
  sla_due_at?: string | null;
  sla_breached_at?: string | null;
  assignee_username?: string | null;
  claimed_by_username?: string | null;
  claimed_at?: string | null;
  escalated: boolean;
  confidence: number;
}

export interface DraftVersion {
  version_no: number;
  subject: string;
  body_masked: string;
  created_at: string;
  id: string;
}

export interface ChunkItem {
  chunk_id: string;
  paragrafus: string;
  quote?: string;
  idezet?: string;
  dok_tipus: string;
  kozertheto_magyarazat?: string;
  score?: number;
  retrieval_source?: RetrievalSource;
  cross_refs?: string[];
}

export type RetrievalSource =
  | "qdrant_semantic"
  | "hybrid_local"
  | "reference_closure"
  | "parent_context"
  | "auto_merged"
  | "empty"
  | string;

export interface SourceRef {
  ref: string;            // "S1", "S2", ...
  chunk_id: string;
  dok_cim?: string;
  dok_tipus?: string;
  paragrafus?: string;
  oldalszam?: number;
  idezet: string;
  magyarazat?: string;
  score?: number;
  retrieval_source?: RetrievalSource;
  used: boolean;
}

export type GenerationMode = "llm" | "insufficient" | "template";

export interface TimelineStep {
  step: string;
  output: Record<string, unknown>;
  mode?: string;
  status?: string;
  counts?: Record<string, unknown>;
  warnings?: string[];
  summary?: string;
}

export interface EscalationState {
  required: boolean;
  reasons: string[];
}

export interface VerifyClaim {
  claim: string;
  grounded: boolean;
  chunk_id?: string;
}

export interface VerifyState {
  claims: VerifyClaim[];
  ungrounded_count: number;
  missing_mandatory?: string[];
  warning?: string;
  verify_mode?: string;
}

export type UnresolvedReference = string | {
  raw?: string;
  doc_hint?: string;
  paragraph?: string;
  [key: string]: unknown;
};

export interface AgentState {
  retrieval: { chunks: ChunkItem[]; unresolved_refs: UnresolvedReference[]; retrieval_mode?: string };
  policy_map: { policy_items: unknown[]; missing_mandatory?: string[]; mandatory_refs?: unknown[] };
  timeline: TimelineStep[];
  draft: {
    subject: string;
    body_masked: string;
    citations: string[];
    sources?: SourceRef[];
    generation_mode?: GenerationMode;
    format?: "email" | "copilot";
  };
  escalation: EscalationState;
  verify: VerifyState;
}

export interface CustomerCandidateItem {
  customer_name: string;
  customer_id: string;
  link_url: string;
}

export interface Case {
  case_id: string;
  category_label: string;
  priority: Priority;
  confidence: number;
  escalated: boolean;
  channel_label: string;
  status_label: string;
  sla_days_remaining: number;
  sla_due_at?: string | null;
  sla_breached_at?: string | null;
  assignee_username?: string | null;
  claimed_by_username?: string | null;
  claimed_at?: string | null;
  sender_email_masked: string;
  sender_email_key: string;
  sender_email_display: string;
  inbound_text_masked: string;
  service_provider?: string;
  customer_candidates: CustomerCandidateItem[];
  draft_versions: DraftVersion[];
  agent_state: AgentState;
}

export interface HistoryItem {
  date: string;
  subject: string;
  category: string;
  status: string;
}

export interface EscalatedItem {
  case_id: string;
  priority: Priority;
  sla_days_remaining: number;
  sla_due_at?: string | null;
  sla_breached_at?: string | null;
  assignee_username?: string | null;
  claimed_by_username?: string | null;
  claimed_at?: string | null;
  subject: string;
  escalation_reason?: string;
}

export interface KpiValues {
  faithfulness?: number;
  citation_support_rate?: number;
  judge_score?: number;
  coverage?: number;
  escalation_appropriateness?: number;
  retrieval_support?: number;
  time_to_answer_ms_p95?: number;
  out_of_scope_answer_rate?: number;
  [key: string]: number | undefined;
}

export interface EvalResult {
  run_id: string;
  aszf_version: string;
  kpis: {
    values: KpiValues;
    status: Record<string, KpiStatus>;
    targets: Record<string, number>;
  };
  results: Array<{ email_id: string; [key: string]: unknown }>;
  baseline_diff: { has_baseline: boolean; diff: Record<string, unknown> };
}

export interface AuditEvent {
  id: number;
  case_id: string;
  event_type: string;
  actor_user_id?: number | null;
  actor_username?: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface AuditCompleteness {
  case_id: string;
  complete: boolean;
  missing: string[];
  required_fields: string[];
}

export interface AuditCaseRecord {
  case_id: string;
  status?: string;
  priority?: string;
  events: AuditEvent[];
  iterations: AuditEvent[];
  latest_iteration?: Record<string, unknown>;
  audit_meta?: Record<string, unknown>;
}

export interface TraceEvent {
  name: string;
  case_id?: string | null;
  duration_ms?: number | null;
  payload: Record<string, unknown>;
  created_at: string;
  backend?: string;
}

export interface AgentStreamEvent {
  event: "start" | "step" | "complete" | "error" | string;
  data: Record<string, unknown>;
}

export interface CaseAssignmentResult {
  case_id: string;
  assignee_username?: string | null;
  claimed_by_username?: string | null;
  claimed_at?: string | null;
}

export interface CopilotSessionItem {
  session_id: string;
  username?: string | null;
  case_id?: string | null;
  turn_count: number;
  last_content_masked?: string;
  created_at: string;
  updated_at: string;
}

export interface AszfKnowledgeItem {
  chunk_id: string;
  section: string;
  paragrafus: string;
  dok_tipus?: string;
  dok_cim?: string;
  oldalszam?: number;
  quote: string;
  text?: string;
  cross_refs: string[];
  source_file?: string;
  score?: number;
}

export interface AszfKnowledgeGroup {
  section: string;
  label: string;
  count: number;
  items: AszfKnowledgeItem[];
}

export interface AcceptanceResult {
  passed: boolean;
  kpi_checks: Record<string, { value: number; rule: [string, number]; passed: boolean }>;
  kpi_failures: string[];
  demo_failures: string[];
  eval_run_id?: string;
  targets: Record<string, unknown>;
}

export interface SupervisorStats {
  total_cases: number;
  escalated_cases: number;
  closed_cases: number;
  escalation_rate: number;
  by_operator: Array<{ username: string; processed: number }>;
}

export interface OcrResult {
  ocr_text_masked: string;
  ocr_confidence: number;
  low_conf_spans: Array<{ start: number; end: number }>;
}

export interface CopilotChatResponse {
  reply: string;
  sources?: SourceRef[];
  draft?: { generation_mode?: GenerationMode } | null;
  timeline: TimelineStep[];
  orchestrator_mode: "llm" | "fallback";
}
