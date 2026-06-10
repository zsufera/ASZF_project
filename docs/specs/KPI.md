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
