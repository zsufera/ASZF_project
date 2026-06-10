# ÁSZF Q&A Agent — Szerződés-specek (implementáció előtt)

> Cél: a kódolás előtti „fix szerződések” rögzítése, hogy a backend, agent és UI párhuzamosan is konzisztensen épülhessen.
> Kapcsolódó: `ASZF_QnA_Agent_megvalositasi_terv.md`, `ASZF_QnA_Agent_frontend_spec.md`, `ASZF_QnA_Agent_prompt_katalogus.md`.

## 1) SQLite adatmodell (v1)

### Fő táblák
- `users`
  - `id`, `username` (unique), `password_hash`, `role` (`ui` / `supervisor`), `is_active`, `created_at`
- `cases`
  - `id`, `case_code` (unique), `channel` (`email|chat|phone|postal`)
  - `status` (`uj|folyamatban|eszkalalva|jovahagyasra_var|lezarva`)
  - `priority` (`surgos|normal`), `confidence`, `escalated` (bool), `escalation_reasons` (json)
  - `sender_email_masked`, `service_provider` (ONE/helyi_kabeles/AH_Media/Invitech)
  - `selected_customer_id` (nullable), `created_at`, `updated_at`
- `messages`
  - `id`, `case_id` (fk), `direction` (`inbound|draft|outbound_mock`)
  - `raw_text_masked`, `channel_payload` (json; postai ágon OCR adatokkal)
  - `language`, `message_type` (`panasz|nem_panasz`)
  - `created_at`
- `draft_versions`
  - `id`, `case_id` (fk), `version_no`, `subject`, `body_masked`
  - `output_mode` (`automata|hitl`), `disclaimer_applied` (bool)
  - `citations` (json), `verify_result` (json), `created_by_user_id`, `created_at`
- `history_links`
  - `id`, `case_id` (fk), `related_case_id` (fk), `reason` (`same_sender_email`)
- `customer_candidates`
  - `id`, `case_id` (fk), `source` (`mock|integration`), `customer_id`, `customer_name`, `link_url`
  - `selected` (bool), `created_at`
- `agent_runs`
  - `id`, `case_id` (fk), `prompt_version_bundle`, `model_profile`
  - `state_snapshot` (json), `started_at`, `ended_at`
- `audit_events`
  - `id`, `case_id` (fk), `event_type`, `actor_user_id` (nullable), `payload` (json), `created_at`

### Minimum indexek
- `cases(status, priority, updated_at desc)`
- `cases(channel, created_at desc)`
- `messages(case_id, created_at)`
- `customer_candidates(case_id, selected)`
- `audit_events(case_id, created_at)`

---

## 2) API szerződések (FastAPI)

## Kötelező közös mezők
- Request header: `X-User-Id`, `X-Role`
- Response meta: `request_id`, `model_profile`, `prompt_version` (ahol releváns)

### Core endpointok
- `POST /ocr`
  - input: `case_id`, `pdf_file`
  - output: `ocr_text_masked`, `ocr_confidence`, `low_conf_spans[]`
- `GET /history?address=...`
  - output: `items[]` (date, subject, category, status, case_id), `summary_masked`, `is_repeated`
- `GET /customer-lookup?address=...`
  - output: `candidates[]` (`customer_id`, `customer_name`, `link_url`, `source`)
- `POST /classify`
  - input: `case_id`, `message_text_masked`, `history_summary_masked?`
  - output: `category`, `subtype`, `confidence`, `candidates[]`, `is_repeated`
- `POST /retrieve`
  - input: `case_id`, `query_masked`, `service_provider?`, `customer_id?`
  - output: `chunks[]` (`chunk_id`, `dok_tipus`, `paragrafus`, `quote`, `score`)
- `POST /policy-map`
  - input: `case_id`, `category`, `chunks[]`
  - output: `policy_items[]`, `mandatory_refs[]`, `missing_mandatory[]`
- `POST /draft`
  - input: `case_id`, `output_mode`, `policy_map`, `actions[]`
  - output: `subject`, `body_masked`, `citations[]`, `disclaimer_applied`
- `POST /verify`
  - input: `case_id`, `draft_body_masked`, `chunks[]`, `mandatory_refs[]`
  - output: `claims[]`, `ungrounded_count`, `missing_mandatory[]`, `warning`
- `POST /unmask`
  - input: `case_id`, `draft_version_id`
  - output: `subject_unmasked`, `body_unmasked`
- `POST /reindex`
  - input: `force` (bool)
  - output: `aszf_version`, `indexed_docs`, `indexed_chunks`, `started_at`, `finished_at`

---

## 3) LangGraph állapot-séma (v1)

```json
{
  "case_id": "string",
  "channel": "email|chat|phone|postal",
  "input_text_masked": "string",
  "history_summary_masked": "string|null",
  "customer_candidates": [],
  "selected_customer_id": "string|null",
  "lang_type": {"nyelv": "hu|en|...", "tipus": "panasz|nem_panasz"},
  "classification": {"category": "string", "confidence": 0.0, "is_repeated": false},
  "priority": {"value": "surgos|normal", "reason": "string"},
  "retrieval": {"chunks": []},
  "policy_map": {"items": [], "mandatory_refs": [], "missing_mandatory": []},
  "escalation": {"required": false, "reasons": []},
  "actions": [],
  "draft": {"subject": "string", "body_masked": "string", "citations": []},
  "verify": {"ungrounded_count": 0, "missing_mandatory": [], "warning": null},
  "audit_refs": {"prompt_version": "string", "model_profile": "string"}
}
```

---

## 4) Konfig-szerződések (minimum kulcsok)

- `config/policies.yaml`
  - `confidence_threshold`
  - `escalation_triggers[]`
  - `sla_fallback_days`
- `config/mandatory_refs.yaml`
  - `category -> required_refs[]`
- `config/disclaimer.yaml`
  - `automata_required: true`
  - `text_hu`
- `config/doc_sources.yaml`
  - `source_pages[]`, `manual_pdf_urls[]`, `local_pdf_dir`
- `config/users.yaml`
  - `users[]` (`username`, `role`, `password_hash`)

---

## 5) Döntési szabályok (UI + backend)

- `díjemelés` kategória **nem** eszkaláció szinonima; külön fogalmak.
- Eszkaláció kötelező, ha:
  - `confidence < threshold`, vagy
  - `policy_map` nem ad fedezetet, vagy
  - trigger találat (egyedi szerződés, vitatott összeg, ismétlődő panasz, SLA).
- HITL módban disclaimer opcionális; automata módban kötelező.
- Postai csatornán az OCR eredmény **ÜI jóváhagyás/javítás után** léphet tovább.

---

## 6) Készre jelentési kritérium a szerződés-spechez

- A backend, UI és agent ugyanazokat az enumokat és mezőneveket használja.
- A `prompt_katalogus` JSON kimenete megfelel a LangGraph állapot-sémának.
- Az audit esemény minden kritikus döntésnél tartalmaz: `case_id`, `actor`, `event_type`, `payload`, `timestamp`.
