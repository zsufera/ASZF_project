# ÁSZF Q&A Agent — Demó forgatókönyv (POC)

## Előkészítés

1. `docker compose up -d` (Qdrant)
2. `python -m backend.db`
3. `uvicorn backend.main:app --reload`
4. Opcionális legacy UI: `streamlit run legacy/ui/app.py` (`ui_demo` / `ui_demo`)

## Automatizált demó-szcenáriók

```bash
python -m demo
```

Vagy API-n: `POST /demo/run`

| ID | Cím | Ellenőrzés |
|----|-----|------------|
| `szamlazas_e2e` | Számlázási panasz végpontig | kategória, draft, források |
| `egyedi_szerzodes_eszkalacio` | Egyedi szerződés gyanú | eszkaláció kötelező |
| `sla_lejarat_eszkalacio` | SLA-lejárat | `sla_lejart` ok |
| `phone_copilot` | Telefon copilot | Beszédpontok formátum |

Riport: `data/demo/latest_demo_report.json`

## Manuális UI demó (15 perc)

### 1. Számlázási panasz (5 perc)

1. Inbox → `email-001-szamlazas-one`
2. Feldolgozás → források panel, draft, idővonal
3. Jóváhagyás mock küldéssel

### 2. Egyedi szerződés eszkaláció (4 perc)

1. Inbox → `email-edge-001-egyedi-szerzodes`
2. Feldolgozás → eszkalációs okok (`egyedi_szerzodes_gyanu`)
3. Supervisor nézet → eszkalált sor

### 3. SLA eszkaláció (3 perc)

1. Szabad bevitel → SLA lejárt jelölő bekapcsolása
2. Feldolgozás → `sla_lejart` az eszkalációs okok között

### 4. Telefon copilot (3 perc)

1. Csatornák → Telefon
2. Számlázási kérdés bevitele → Beszédpontok + forráshivatkozások

## Elfogadási kapu

```bash
python scripts/run_quality_gate.py
```

API: `POST /acceptance/run` — eval KPI-k + demó-szcenáriók együtt.

## Observability

- Agent futások: `GET /observability/traces`
- Lokális trace fájlok: `data/traces/trace-YYYYMMDD.jsonl`
- Opcionális Langfuse: `docker compose --profile observability up -d`, `.env`: `LANGFUSE_ENABLED=true`
