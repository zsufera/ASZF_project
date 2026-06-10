# ÁSZF Q&A Agent — Compliance ellenőrzőlista (POC)

> Kapcsolódó: [dpia.md](dpia.md), `config/retention.yaml`, `security/`

## Adatvédelem és PII

- [x] Maszkolás minden felhős/LLM egress előtt (regex POC)
- [x] Unmask csak RBAC mögött, naplózva (`pii_unmask_access`)
- [x] Audit payload redakció (`security/redaction.py`)
- [x] PII-szivárgás kapu teszt (`tests/test_pii_gate.py`)
- [x] DPIA dokumentálva (`docs/governance/dpia.md`)

## GDPR Art. 22

- [x] Automata mód átláthatósági esemény (`gdpr_art22_automated_decision`)
- [x] HITL alapértelmezett kimeneti mód
- [x] Mock küldés — nincs közvetlen ügyfél-kommunikáció

## Audit és governance

- [x] Iterációs audit rekord (`case_iteration`)
- [x] Státusz workflow validáció
- [x] Megőrzési policy + purge dry-run
- [x] Audit teljesség ellenőrzés endpoint

## Biztonság

- [x] Prompt-injection detektálás (`/classify`)
- [x] RBAC szerepkörök (`ui` / `supervisor`)
- [x] Hatókörön kívüli / adversariális edge-case tesztek

## Observability (POC)

- [x] Lokális JSON trace (`backend/tracing_service.py`)
- [ ] Langfuse éles bekötés (opcionális compose profile)

## Elfogadási kapuk

- [x] Eval harness KPI-k (`POST /eval/run`)
- [x] Demó-szcenáriók (`demo/runner.py`)
- [x] Acceptance futtatás (`POST /acceptance/run`, `scripts/run_quality_gate.py`)
