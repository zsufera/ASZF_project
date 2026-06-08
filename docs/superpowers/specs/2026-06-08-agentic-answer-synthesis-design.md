# Agentic válasz-szintézis + gazdag forrás-megjelenítés — Design

> **Dátum:** 2026-06-08
> **Cél:** Az ügyintézői copilot mind a chat/telefon, mind az email úton **koherens, az ügyfél/ügyintéző számára értelmes választ** adjon — ne a RAG által visszaadott dokumentum-idézetek nyers felsorolását. A szabad szöveges válasz mellett a forrásdokumentumok (azonosító, dokumentumnév, paragrafus, oldalszám, szó szerinti idézet, közérthető magyarázat) **kattintható, lenyitható, kellemes UI-ban** jelenjenek meg.
> **Érintett rétegek:** agentic réteg (`agent/nodes.py`, `backend/draft.py`) + React frontend. **Backend HTTP-szerződés nem változik** (a `draft` objektum bővül, a végpontok azonosak).

---

## 0. Probléma (gyökérok)

A jelenlegi kód két külön úton készít „választ", és mindkettő nyers RAG-idézeteket sorol fel bizonyos esetekben:

1. **Copilot (chat/telefon)** — `agent/nodes.py` → `draft_node`: bedrótozott idézet-darabokat fűz össze (`f"• {item['idezet'][:180]} (forrás: {item['chunk_id']})"`), **soha nem hív LLM-et**. Ez a fő hibás pont — ezt látja a felhasználó a copilotban.
2. **Email** — `backend/draft.py` → `build_draft`: LLM-mel koherens levelet ír, **de** ha nincs `policy_items` vagy az LLM-hívás kivételt dob, **csendben** visszaesik a `build_draft_template`-re, ami szintén idézet-lista.
3. **A forrás-metaadat megvan** (`chunk_id`, `dok_cim`, `dok_tipus`, `paragrafus`, `oldalszam`, `quote`/`idezet`, `score`), de a UI nagy részét eldobja, és csak a chunk_id-t mutatja a szövegben.

## 1. Döntések (jóváhagyott)

| # | Döntés | Választott irány |
|---|---|---|
| 1 | Válasz ↔ forrás összekötése | **Inline `[S1]` jelölők a szövegben + gazdag forrás-panel** (RAG „answer with citations" minta) |
| 2 | Forrás-kártya részletessége | **Gazdag, lenyitható** (tömör fejléc, igény szerint mély) |
| 3 | Fallback (nincs LLM / nincs találat / LLM-hiba) | **Őszinte jelzés + eszkaláció-javaslat**, nincs ál-válasz idézetekből; a megtalált források ettől függetlenül megjelennek |
| 4 | Megközelítés | **„A": egységesített `synthesize_answer()` node, 1 LLM-hívás/válasz** |

**Implementátor által eldöntött, jóváhagyott részletek:**
- Az **email-levél** az approve/unmask lépésnél tisztul: a `[S1]` jelölők eltávolításra kerülnek, így az ügyfélhez tiszta szöveg megy ki, miközben az ügyintéző a szerkesztőben látja a fedezetet.
- A **copilot-válasz** az **ügyintézőnek** szól (belső kopilót), nem közvetlen ügyfél-szöveg — összhangban a meglévő `SYSTEM_PREAMBLE` kerettel.

## 2. Architektúra

```
                    ┌──────────────────────────────────────────┐
                    │  agent/nodes.py :: draft_node             │
                    │  (email ÉS chat/telefon — EGYSÉGES)       │
                    └───────────────────┬──────────────────────┘
                                        │ policy_map.policy_items + classification + channel
                                        ▼
                    ┌──────────────────────────────────────────┐
                    │  backend/draft.py :: synthesize_answer()  │
                    │  1) sources[] összeállítása ref-ekkel     │
                    │  2) LLM-hívás (chat_json) → answer+[Sn]    │
                    │  3) fallback ágak (insufficient/template)  │
                    └───────────────────┬──────────────────────┘
                                        ▼
                    draft = { subject, body_masked([Sn]),
                              sources[], citations[], generation_mode, format }
                                        │
              ┌─────────────────────────┴─────────────────────────┐
              ▼ (/agent/run → copilot)              ▼ (state_snapshot → get_case_detail → email ügy)
   React: InlineAnswer + SourceCard panel   React: DraftEditor + SourceCard panel + approve-strip
```

### Egységek és felelősségek

- **`synthesize_answer(...)`** (`backend/draft.py`, ÚJ — a `build_draft` ezt váltja/wrappeli): bemenet a maszkolt szöveg, a `policy_items`, a kategória, a csatorna és az output_mode; kimenet az egységes `draft` szerkezet. **Egyetlen LLM-hívás.** Tiszta függvény (a `chat_json`-on kívül nincs mellékhatása), külön tesztelhető.
- **`draft_node`** (`agent/nodes.py`): csak orchestrál — a chat/telefon bedrótozott ága **törölve**, mindkét csatorna a `synthesize_answer()`-t hívja csatorna-paraméterrel.
- **`strip_source_markers(text)`** (`backend/draft.py`, ÚJ): a `[S1]…[Sn]` tokeneket eltávolítja; az approve/unmask úton hívjuk.
- **`InlineAnswer`** (React, ÚJ): a `body_masked`-et szegmensekre bontja a `[Sn]` jelölők mentén, és kattintható chip-eket renderel.
- **`SourceCard`** (React, bővített): gazdag, lenyitható forrás-kártya.

## 3. Adat-szerződés — a `draft` objektum (bővítve)

```jsonc
{
  "subject": "Válaszjavaslat felmondás ügyben",
  "body_masked": "A vezetékes szerződés rendes felmondása 60 napos határidővel lehetséges [S1]. A hűségidő alatti felmondásnál a kapott kedvezmény visszafizetése merülhet fel [S2].",
  "sources": [
    {
      "ref": "S1",
      "chunk_id": "doc_b74e87e45de13120_p0094_s004",
      "dok_cim": "Általános Szerződési Feltételek (vezetékes)",
      "dok_tipus": "ASZF",
      "paragrafus": "8.4",
      "oldalszam": 94,
      "idezet": "Az előfizető a határozatlan idejű szerződést 60 napos felmondási idővel mondhatja fel...",
      "magyarazat": "Ez a szakasz a rendes (határidős) felmondás feltételeit szabályozza.",
      "score": 0.82,
      "used": true
    }
  ],
  "citations": ["doc_b74e87e45de13120_p0094_s004"],   // visszafelé-kompatibilis lapos lista
  "generation_mode": "llm",        // "llm" | "insufficient"  (ÚJ)
  "format": "email",               // "email" | "copilot"
  "disclaimer_applied": false
}
```

**Megjegyzések:**
- A `sources[]` **rendezett**; a `ref` (`S1`, `S2`, …) a `body_masked` jelölőivel egyezik. A `used` jelzi, hogy az LLM ténylegesen hivatkozott-e rá (a nem-hivatkozott, de megtalált források is megjelennek, halványabban).
- A `citations` (lapos chunk_id-lista) megmarad a meglévő `verify_node` és a régi UI-mezők kompatibilitása miatt.
- `generation_mode` (a 3. döntéssel összhangban **nincs idézet-dump fallback**):
  - `llm` — valódi szintézis.
  - `insufficient` — nincs LLM / nincs forrás / LLM-hiba / üres vagy elégtelen-fedezetű LLM-válasz → őszinte jelzés, nincs ál-válasz. A megtalált források ettől függetlenül megjelennek.

## 4. Agentic réteg — részletek

### 4.1 `synthesize_answer()` (`backend/draft.py`)

Folyamat:
1. **`sources[]` összeállítása** a `policy_items`-ből: minden elemhez `ref = f"S{i+1}"`, és a meglévő mezők (`chunk_id`, `dok_cim`, `dok_tipus`, `paragrafus`, `oldalszam`, `idezet`, `magyarazat`, `score`). Kezdetben `used=False`.
2. **Fallback-kapu:** ha `not llm_available()` **vagy** `not sources` → `generation_mode="insufficient"`, `body_masked` = rögzített, őszinte üzenet (csatorna-specifikus), `sources` változatlanul visszaadva (ha volt találat). **Nincs idézet-dump.**
3. **LLM-hívás** (`chat_json`): a prompt forrás-blokkja `[S1] "idézet" (dok_cim §paragrafus)` formátumú; az utasítás: koherens válasz, minden tartalmi állítás mögé `[Sn]` jelölő, csak a megadott forrásokra alapozva. JSON-séma: `{ "targy", "valasz", "felhasznalt_forrasok": ["S1", ...], "elegtelen_fedezet": bool }`.
4. **Utófeldolgozás:** a `valasz` üres VAGY `elegtelen_fedezet=true` → `insufficient` (őszinte jelzés, **nem** idézet-dump). Egyébként: a `used_sources` alapján a `sources[].used` beállítása; csak a ténylegesen létező `Sn` jelölők maradnak (érvénytelen jelölő törlése).
5. **Csatorna-specifikus utasítás:**
   - `email`: hivatalos magyar válaszlevél (megszólítás, törzs, javasolt intézkedés, aláírás), maszkolt PII megtartva.
   - `chat`/`phone`: tömör, ügyintézőnek szóló koherens válasz/beszédpont-narratíva (nem közvetlen ügyfél-levél).

### 4.2 `draft_node` (`agent/nodes.py`)

A jelenlegi `if channel in {"chat","phone"}: …` bedrótozott ág **törölve**. Helyette:
```python
result = synthesize_answer(
    case_id=state["case_id"],
    category=category,
    channel=channel,
    output_mode=output_mode,
    policy_map=policy_map,
    actions=actions,
)
```
A timeline-bejegyzés bővül: `{"format", "citation_count", "source_count", "generation_mode"}`.

### 4.3 Jelölő-tisztítás jóváhagyáskor

A `strip_source_markers(text)` regex `\[S\d+\]` mintát töröl (a környező felesleges szóközöket normalizálva). Az approve/unmask úton (`backend/case_service.py` approve-ág és/vagy `agent/nodes.py::prepare_unmask`) a kimenő ügyfél-szövegre alkalmazzuk. **Az ügyintézői (maszkolt, szerkesztett) draft megtartja a jelölőket; csak a kiküldendő ügyfél-levél tisztul.**

## 5. Frontend — részletek

### 5.1 Típusok (`frontend/src/lib/types.ts`)
- `SourceRef` (ÚJ): `ref, chunk_id, dok_cim, dok_tipus, paragrafus, oldalszam?, idezet, magyarazat?, score?, used`.
- `AgentDraft` bővítve: `sources?: SourceRef[]`, `generation_mode?: "llm" | "insufficient"`, `format?: "email" | "copilot"`.

### 5.2 `InlineAnswer` (ÚJ komponens)
- Bemenet: `body` (string `[Sn]` jelölőkkel), `sources`, `onCite(ref)`.
- A `[Sn]` tokeneket türkiz, kattintható chip-ekké alakítja (a `Badge`/chip stílussal). Kattintásra `onCite(ref)` → a megfelelő `SourceCard`-ra görget + 1.5 mp kiemelés (a meglévő `sourceRefs` minta a `CaseWorkstation`-ben).
- Ismeretlen/érvénytelen `ref` → semleges szövegként jelenik meg (nem törik el).

### 5.3 `SourceCard` (bővített)
- **Fejléc (mindig):** `ref` chip + `dok_cim` + `§paragrafus` + relevancia (score → „magas/közepes" vagy %), `used=false` esetén halványítva.
- **Lenyitva:** `dok_tipus`, `oldalszam`, **szó szerinti idézet** (idézőjelben, halvány háttér), közérthető magyarázat, és a `chunk_id` másolható (kis „másolás" gomb).
- Lenyitás állapota lokális; a11y: `button` + `aria-expanded`.

### 5.4 Képernyők
- **`Copilot.tsx`:** az asszisztens-buborék a szintetizált választ `InlineAnswer`-rel rendereli; a jobb oldali panel a gazdag `SourceCard`-okat mutatja. `insufficient` → figyelmeztető banner a buborék fölött. A szimulált soronkénti streamelés megmarad, de a `[Sn]` jelölők a végső (nem-streamelő) renderben válnak chip-ekké.
- **`CaseWorkstation.tsx` / `DraftEditor.tsx`:** a draft előnézete `InlineAnswer`; a források a bal panelen gazdag kártyaként. `insufficient` → a meglévő eszkalációs sávval összhangban banner. A citation-kattintás a meglévő `handleCitationClick` helyett/mellett a `ref`-alapú scrollt használja.
- **Fallback banner:** `generation_mode==="insufficient"` → türkiz helyett figyelmeztető (status-esc) sáv: *„Nincs elég ÁSZF-fedezet automatikus válaszhoz — emberi ellenőrzés / eszkaláció javasolt."*

## 6. Hibakezelés
- LLM-timeout/kivétel → `synthesize_answer` elkapja → `insufficient`, soha nem propagál 500-at.
- Üres `sources` + LLM elérhető → `insufficient` (nincs miből alapozni).
- Frontend: hiányzó `sources`/`generation_mode` (régi snapshot) → biztonságos default (`[]`, `"llm"` feltételezés nélkül a banner nem jelenik meg); az `InlineAnswer` jelölő nélkül is helyesen renderel.

## 7. Tesztelés
**Backend (pytest):**
- `synthesize_answer` LLM-mockkal: a `valasz` `[Sn]` jelölői ↔ `sources[].ref` konzisztensek; `used` helyesen jelölve.
- Fallback-ág: `llm_available=False` → `generation_mode="insufficient"`, nincs „(forrás: …)" idézet-dump a body-ban.
- Üres `policy_items` → `insufficient`.
- `strip_source_markers`: `[S1]` tokenek eltűnnek, a szöveg ép marad.
- `draft_node` chat ÉS email csatornán → mindkettő `synthesize_answer`-t használ (a régi bedrótozott „Beszédpontok:" prefix már nem jelenik meg).

**Frontend (tsc + build):**
- `InlineAnswer` marker-parser: `[S1]`/`[S2]` chip-ekké; ismeretlen ref biztonságos.
- Tiszta `tsc --noEmit` és `vite build`.

## 8. Hatókörön kívül (YAGNI)
- Valódi token-streamelés (SSE) — külön follow-up; marad a szimulált soronkénti.
- Mondat-szintű, LLM-alapú utólagos citation-illesztés (2× hívás) — elvetve költség miatt.
- `<mark>` kiemelés a bejövő szövegben — változatlanul follow-up.
- Az embedding/retrieval réteg nem változik.
