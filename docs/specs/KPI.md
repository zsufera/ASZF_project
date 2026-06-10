# Sikerességi kritériumok és KPI-ok

## A PoC sikeresnek tekinthető, ha:

| KPI | Célérték | Mérés módja | Forrás |
|-----|----------|-------------|--------|
| Kategória-osztályozás pontossága | ≥ 80% | Eval harness: helyes `fo_kategoria` a mintán | `POST /eval/run` |
| Forrásoltság (citation support rate) | ≥ 95% | A draft-ban hivatkozott chunk-ok hányada, amit a verify lépés megalapozottnak ítél | `config/eval_targets.yaml` |
| Lefedettség (coverage) | ≥ 80% | A mintaüzenetek hányada, amelyre a rendszer érdemi (nem „insufficient") draftot ad | `config/eval_targets.yaml` |
| Eszkaláció-helyesség | ≥ 90% | Az eszkalációs döntések hányada, amely megfelel a szabályzati triggerlistának | `config/eval_targets.yaml` |
| PII-maszkolás teljessége | 100% | Egyetlen LLM-prompt, log vagy audit-payload sem tartalmaz maszkolatlan PII-t | `tests/test_masking.py`, kézi audit |
| Válaszidő (P95) | ≤ 30 s | A teljes agent pipeline futásideje a 95. percentilisen | `POST /acceptance/run` |

## Mérési infrastruktúra

- **Eval harness**: `POST /eval/run` futtatja a `data/sample_emails/` mintákon; eredmény: `data/eval/runs/`.
- **Baseline**: `POST /eval/baseline` a korábbi futás eredményét menti referenciának.
- **Acceptance gate**: `POST /acceptance/run` az összes KPI-t egyben ellenőrzi; a `scripts/run_quality_gate.py` CLI-ből hívható.
- **Human score**: `POST /eval/human-score` emberi pontszámot társít az eval-futáshoz.

## Szabályalapú vs. LLM-út összehasonlítás

Az eval kimenete tartalmazza a `*_mode` mezőket (`classify_mode`, `generation_mode`, `verify_mode`), amelyekből kiszámítható, hogy az adott mintán melyik út futott. Ezzel a szabályalapú fallback és az LLM-út teljesítménye összevethető ugyanazon a mintahalmazon.

## Operatív (visszamérési) KPI-k

A fenti, fejlesztési idejű eval-KPI-kkal szemben az alábbiak az élő használatot mérik,
a már rögzített audit-adatokból (`audit_events`, `cases`, `draft_versions`) új
adatgyűjtés nélkül. Forrás: `GET /metrics/operational`, UI: "Visszamérés" képernyő.

| KPI | Mit mér | Számítás |
|-----|---------|----------|
| Átfutási idő (AHT) | Agent-feldolgozástól a jóváhagyásig eltelt idő | `case_iteration` -> `draft_approved_mock_send` audit-timestampek deltája (átlag, medián) |
| Copilot-lefedettség | A pipeline-nal feldolgozott ügyek aránya | draft-verzióval rendelkező ügyek / összes ügy |
| Draft-átvételi sávok | Mennyit szerkeszt az ügyintéző a drafton | első vs. utolsó draft-verzió normalizált diffje (`difflib`); <5% változtatás nélkül, <30% kis szerkesztés, fölötte újraírás |
| Pozitív visszajelzés | jó / (jó + rossz) arány | `ui_feedback` audit-eventek |
| Negatív okkódok | Mi a rossz visszajelzés oka | fix okkódlista: pontatlan / hiányos / rossz hangnem / rossz forrás / felesleges eszkaláció |
| Eszkalációs arány | Eszkalált ügyek aránya | `cases.escalated` |

## LLM-bíró (szöveg-jóság)

Az eval harness minden mintán a heurisztikus `judge_score` mellett LLM-bírót is futtat
(`eval/llm_judge.py`, kapcsoló: `LLM_JUDGE_ENABLED`): dimenziónkénti 1-5 pontozás
(forráshűség, teljesség, hangnem, közérthetőség) és indoklás. Aggregált KPI:
`llm_judge_score` és `llm_judge_coverage`. Kalibráció: az Evaluation képernyő emberi
1-5 pontozása összevethető az LLM-bíró átlagával; az eltérés a bíró megbízhatóságát jelzi.
