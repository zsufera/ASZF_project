# Backend API-kontraktus (a frontend nézőpontjából)

> A meglévő **FastAPI** backend végpontjai és a frontend által használt válasz-mezők.
> Forrás: a Streamlit POC `ui/api_client.py` hívásai + a nézetekben olvasott mezők.
> **Mérvadó forrás:** futó backend mellett `GET /openapi.json` és a `/docs` (Swagger UI).
> Bázis URL: `BACKEND_URL` env (POC: `http://127.0.0.1:8000`).
> Minden válasz hordoz egy közös burkot: `request_id`, `model_profile`, `prompt_version`, `aszf_version`.

## Auth & rendszer
| Metódus | Útvonal | Kérés | Válasz (lényeg) |
|---|---|---|---|
| POST | `/auth/login` | `{username, password}` | `{username, role}` vagy `{error}` — `role ∈ {"ui","supervisor"}` |
| GET | `/health` | — | `{aszf_version, ...}` |
| POST | `/reindex` | `{force: bool}` | `{indexed_chunks: int}` |

## Inbox & ügyek
| Metódus | Útvonal | Kérés | Válasz (lényeg) |
|---|---|---|---|
| GET | `/inbox` | query: `category, priority, status, channel, search, sort_by` | `{items: InboxItem[]}` |
| GET | `/cases/{case_id}` | — | `Case` (lásd lent) |
| POST | `/cases/create` | `{channel, input_text, sender_email?, service_provider?}` | `{case_id}` |
| POST | `/cases/process` | `{case_id, output_mode, username, service_provider?, input_text_masked?}` | `AgentResult` |
| POST | `/cases/draft` | `{case_id, subject, body_masked, output_mode, citations, username}` | `{...}` |
| POST | `/cases/approve` | `{case_id, subject_masked, body_masked, username, role, draft_version_id}` | `{subject_unmasked, body_unmasked}` *(RBAC unmask)* |
| POST | `/cases/feedback` | `{case_id, rating, wrong_source?, username}` — `rating ∈ {"jo","rossz"}` | `{...}` |
| POST | `/cases/status` | státusz-workflow | `{...}` |
| GET | `/history` | query: `address` | `{items: HistoryItem[], is_repeated: bool}` |
| GET | `/customer-lookup` | query: `address` | `{candidates: CustomerCandidate[]}` |
| POST | `/ocr` | multipart: `case_id`, `pdf_file` | `{ocr_text_masked, ocr_confidence, low_conf_spans}` |
| POST | `/agent/run` | `{case_id, channel, input_text\|input_text_masked, sender_email?, service_provider?, output_mode}` | teljes agent-folyamat `{timeline[], ...}` |

## Evaluation
| Metódus | Útvonal | Kérés | Válasz (lényeg) |
|---|---|---|---|
| POST | `/eval/run` | `{limit, category?, service_provider?, include_edge}` | `EvalResult` |
| GET | `/eval/runs/{run_id}` | — | `EvalResult` |
| POST | `/eval/baseline` | `{run_id}` | `{...}` |
| GET | `/eval/baseline` | — | `{...}` |
| POST | `/eval/human-score` | `{run_id, email_id, score}` — `score ∈ 1..5` | `{...}` |

## Supervisor & audit
| Metódus | Útvonal | Kérés | Válasz (lényeg) |
|---|---|---|---|
| GET | `/supervisor/queue` | — | `{items: EscalatedItem[]}` |
| GET | `/supervisor/stats` | — | `{total_cases, escalated_cases, closed_cases, escalation_rate, by_operator: [{username, processed}]}` |
| GET | `/audit/cases/{case_id}` | query: `role` | `{iterations: [...]}` |
| GET | `/audit/completeness/{case_id}` | query: `role` | `{...}` |
| GET | `/audit/events` | query: `case_id?, role, limit` | `{...}` |
| POST | `/governance/purge` | `{dry_run, username, role}` | `{...}` |

## Fő adatszerkezetek

### InboxItem
`case_id, category_label, priority ("surgos"|"normal"), status_label, channel_label, subject, sla_days_remaining (int), escalated (bool), confidence (float 0..1)`

### Case (`GET /cases/{id}`)
```
case_id, category_label, priority, confidence, escalated, channel_label,
status_label, sla_days_remaining, sender_email_masked, inbound_text_masked,
service_provider,
customer_candidates: [{ customer_name, customer_id, link_url }],
draft_versions:      [{ version_no, subject, body_masked, created_at, id }],
agent_state: {
  retrieval: { chunks: [{ chunk_id, paragrafus, quote|idezet, dok_tipus, kozertheto_magyarazat }] },
  policy_map: { policy_items: [...] },
  timeline:  [{ step, output: {} }],
  draft:     { subject, body_masked, citations: [] },
  escalation:{ required: bool, reasons: [str] }
}
```

### Agent timeline lépések (`step` értékek, sorrendben)
`language → mask → classify → priority → policy_map → escalation → draft → verify`
- `escalation.output`: `{ required, reasons }`
- `verify.output`: `{ ungrounded_count, ... }`
- minden lépés `output`-ja kibontható, lépés-specifikus JSON.

### EvalResult (`/eval/run`)
```
run_id, aszf_version,
kpis: {
  values:  { faithfulness, citation_support_rate, judge_score, coverage,
             escalation_appropriateness, retrieval_support,
             time_to_answer_ms_p95, out_of_scope_answer_rate },
  status:  { <kpi_kulcs>: "green"|"yellow"|"red" },
  targets: { <kpi_kulcs>: <celertek> }
},
results: [ { email_id, ... per-kérdés metrikák } ],
baseline_diff: { has_baseline: bool, diff: {} }
```

### HistoryItem / CustomerCandidate / EscalatedItem
- `HistoryItem`: `{ date, subject, category, status }`
- `CustomerCandidate`: `{ customer_name, customer_id, link_url }`
- `EscalatedItem`: `{ case_id, priority, sla_days_remaining, subject, ... }`

> **PII / RBAC:** a `*_masked` mezők maszkolt PII-t tartalmaznak. Az unmask (`/cases/approve` válaszában a `*_unmasked`) csak jogosult szerepkörnek jár, és a backend naplózza. A frontend alapból a maszkolt mezőket jeleníti meg.
