---
description: Lefuttatja a backend pytest-et és a frontend típus/build ellenőrzést, és értelmezi az eredményt.
argument-hint: "[opcionális pytest szűrő, pl. tests/test_verify.py]"
---

Futtasd a teszteket és foglald össze az eredményt.

1. **Backend:** `.venv/Scripts/python.exe -m pytest $1 -q` (ha `$1` üres: `tests/`).
   - **Egy ismert, FÜGGETLEN bukás elfogadható:** `tests/test_settings_vector.py::test_settings_have_local_qdrant_defaults` — a lokális `.env` `OPENAI_EMBED_DIM=512` miatt bukik, nem a kód hibája. Minden MÁS bukás valódi regresszió → vizsgáld ki.
   - A teszt-suite hermetikus (a `conftest.py` üres OpenAI-kulcsra kényszerít) → nincs valódi LLM-hívás, hacsak egy teszt expliciten nem opt-inel.
2. **Frontend** (ha frontend-fájl is változott): `cd frontend; npx tsc --noEmit` majd `npm run build` — mindkettőnek tisztán kell lefutnia.
3. Foglald össze: hány zöld, mely (ha van) valódi bukás, és hol. Ne hivatkozz „sikeres tesztre", ha a futtatás nem adott megbízható exit-státuszt (guardrails §9).
