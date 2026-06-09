# ÁSZF Q&A Agent — One-arculatú UI újratervezés (design spec)

> Dátum: 2026-06-07 · Ág: `advanced_ui`
> Kapcsolódó: [ASZF_QnA_Agent_frontend_spec.md](../../../ASZF_QnA_Agent_frontend_spec.md) (eredeti wireframe-spec), [README.md](../../../README.md) (Fázis 4 UI), [FEJLESZTESI_GUARDRAILS.md](../../../FEJLESZTESI_GUARDRAILS.md).

## 1. Cél és hatókör

A meglévő, funkcionálisan kész **Streamlit** ügyintézői copilot (`ui/`) **modern, letisztult újratervezése** a **One Magyarország** arculatára, úgy, hogy a backend funkciói logikusan, jól használhatóan jelenjenek meg.

Négy egyidejű cél (mind a felhasználó kérése):
1. **Vizuális modernizáció** — One-arculat, kártya-alapú, letisztult, hivatalos megjelenés.
2. **Navigáció / IA** — funkciók logikus csoportosítása, gyors megtalálhatóság.
3. **Ügy-munkafolyamat ergonómia** — a háromhasábos ügy-nézet és a feldolgozás gördülékenysége.
4. **Beszélgetős copilot** — chat / telefon copilot natív chat-élményként.

**Platform:** Streamlit (a meglévő ökoszisztéma megtartva). Chainlit **nem** kerül be; opcióként marad, ha később a beszélgetős rész önálló, gazdagabb terméket igényel.

### Hatókörön kívül
- Új backend végpont vagy üzleti funkció (minden szükséges endpoint létezik).
- Valós ügyféltörzs-integráció (POC: mock marad).
- Chainlit bevezetése.
- A `preprocessing/`, `agent/`, `eval/`, `backend/` logikájának módosítása.

## 2. Arculat (One design tokenek)

A One arculata **türkiz + fekete + fehér**, kör alakú kézzel írt „one" logó, flat/rounded, ember-központú megjelenés (forrás: novekedes.hu, kreativ.hu). Pontos márka-hex nem nyilvános, ezért közelítő tokeneket használunk; egy helyen cserélhetők, ha rendelkezésre áll a hivatalos kód.

| Token | Érték | Használat |
|---|---|---|
| `--one-turq` | `#16C7C0` | elsődleges kiemelés: aktív menü, gombok, linkek, fókusz, idővonal-pöttyök |
| `--one-turq-d` | `#0FA39D` | hover / sötétebb türkiz szöveg |
| `--one-turq-l` | `#E3FAF8` | halvány türkiz háttér (badge, kiemelt fejléc) |
| `--one-black` | `#0E1212` | bejelentkező/erős márkamomentum háttere |
| `--one-ink` | `#16201F` | fő szövegszín |
| `--one-grey` | `#6B7A79` | másodlagos szöveg, címkék |
| `--one-line` | `#E2EAE9` | keretek, elválasztók |
| háttér | `#F7FAF9` / `#FFFFFF` | vászon / kártyák |

**Megjelenési elvek:** világos vászon, fehér kártyák lekerekített sarokkal (10–14px), finom árnyék/keret, a türkiz **csak kiemelésre** (nem nagy felületeken — hosszú használatra kíméletes). A fekete sáv a **bejelentkező képernyőn és a fejléc logó-momentumában** jelenhet meg.

**Megvalósítás:**
- `.streamlit/config.toml` `[theme]` blokk: `primaryColor="#16C7C0"`, `backgroundColor`, `secondaryBackgroundColor`, `textColor`, base font.
- `ui/theme.py` (új): a tokeneket Python konstansként és **egyszer injektált CSS-ként** (`st.markdown(..., unsafe_allow_html=True)`) adja a komponensekhez (kártya, badge, ikon-sáv, fejléc, chat-buborék, source-card stílusok).

## 3. Felület-váz (IA) — „Munkaállomás" modell

Keskeny **ikon-sáv** (bal) + **fejléc** (felül) + **főterület**.

```
+---------------------------------------------------------------+
| [one] ÁSZF Copilot | 🔍 keresés | ÁSZF v3.2 | ☁ Felhő | 👤 user |  <- fejléc
+------+--------------------------------------------------------+
| 📥   |                                                        |
| ✏️   |   FŐTERÜLET                                             |
| 💬   |   (inbox-lista  VAGY  teljes ügy-munkaállomás)         |
| 📊   |                                                        |
| 🛡️   |                                                        |
+------+--------------------------------------------------------+
```

- **Ikon-sáv menüpontok (szerepkör-függő):** Inbox · Új ügy · Copilot · Evaluation · (Supervisor — csak supervisor). Megvalósítás: `streamlit-option-menu` komponens, függőleges, ikonokkal; vagy CSS-ezett `st.radio` fallback, ha a komponens nem kívánatos.
- **Fejléc (`top_header` komponens):** „one" logó + alkalmazásnév, globális kereső (ügy-azonosító / feladó), ÁSZF-verzió chip, modell-profil kapcsoló (felhő/on-prem → `PROVIDER`), kimeneti mód alap (HITL/automata), bejelentkezett felhasználó + kijelentkezés, „Újraindexelés" (`/reindex`, megerősítéssel).
- **Navigációs mód (`session_state`):** a főterület két állapotú — `list` (a kiválasztott nézet listája) és `case` (teljes szélességű ügy-munkaállomás). Ügy kiválasztása → `case` mód, `active_case_id` beállítva. **„← Vissza"** gomb → `list` mód. Ez váltja le a jelenlegi „ügy a lista alatt inline" megoldást.

## 4. Nézetek

### 4.1 Bejelentkezés
- One-arculat, **fekete márkamomentum** (logó + türkiz akcentus). Mezők: felhasználónév, jelszó (`users.yaml`). Hibás belépés → hibajelzés. Sikeres belépés után a szerepkör határozza meg a menüt; az ügyintéző neve auditba kerül (változatlan logika).

### 4.2 Inbox (lista mód)
- Szűrő-sor: Kategória · Prioritás · Státusz · Csatorna · Keresés.
- Rendezés: prioritás / SLA / beérkezés.
- Sorok kártyaszerű megjelenéssel; **színkódolt badge-ek**: kategória, prioritás (SÜRGŐS piros), eszkaláció (⚠), alacsony konfidencia; csatorna-ikon; SLA-hátralévő.
- Üres állapot: „Nincs megjeleníthető üzenet."
- Sorra kattintás → ügy-munkaállomás (`case` mód).

### 4.3 Új ügy / szabad bevitel
- Nagy szövegmező (email beillesztése vagy szabad kérdés), opcionális csatorna-választó, „Feldolgozás" → ad-hoc ügy-munkaállomás.

### 4.4 Ügy-munkaállomás (hero, háromhasábos)
Teljes szélességű. Felül **ügyfejléc**: ügyazonosító, kategória/prioritás/konfidencia/eszkaláció badge-ek, feladó (maszkolt), SLA-számláló; halvány türkiz gradiens háttér.

Három oszlop `st.columns([1,2,1])`:

**Bal — kontextus**
- **Források** (`source_card`): § + `dok_tipus`, **szó szerinti idézet**, „közérthető magyarázat" kapcsoló, ⤴ ugrás a teljes szakaszra.
- **Előzmények** (`history_card`): azonos címről érkezett üzenetek (dátum, tárgy, kategória, státusz), ismétlődő-panasz jelzés.
- **Ügyféltörzs-jelöltek** (`customer_card`): név + azonosító, kiválasztó (szolgáltatóra szűkít), ⤴ (mock).

**Közép — tartalom**
- **Bejövő üzenet** a hivatkozandó részek **kiemelésével**.
- **Draft-szerkesztő** (`draft_editor`): szabad szöveg / sablonblokk kapcsoló, verziótörténet legördülő (`v1, v2…`), HITL/automata mód-kapcsoló, kattintható **citationök**, forrás hozzáadása/elvétele, **„✓ Jóváhagyom kiküldésre"** (unmask RBAC → verzió rögzítés → mock küldés → „lezárva"), **visszajelzés** (👍/👎 + „rossz forrás").

**Jobb — agent-idővonal**
- A Fázis 3 node-jai lépésenként, állapot-ikonnal (✓ kész / ⚠ figyelmeztetés / ⟳ fut / ✗ hiba) — `agent_step` komponens.
- **Kinyitható/becsukható, alapból nyitva**: a teljes idővonal egy `st.expander(expanded=True)`-ben (vagy fejléc-toggle). Lépésre kattintva kibomlik a node kimenete (osztályozás-jelöltek, szabályzat-elemek, eszkaláció oka, nem-megalapozott állítások).
- **Eszkaláció** lépésnél kiemelt jelzés + „Eszkaláció supervisorhoz" gomb (ha még nem eszkalált).
- Megjegyzés: az expander becsukása vizuálisan helyet ad; a draft tényleges szélességi reflow-ja (kétoszloposra váltás) opcionális finomítás `session_state`-vezérelt oszloparánnyal — POC-ban elég a becsukás.

### 4.5 Copilot (chat / telefon) — Streamlit-natív
- Csatorna-fülek: **Email · Chat-copilot · Telefon-copilot · Postai**.
- **Natív chat**: `st.chat_message` (ÜI / agent buborékok), `st.chat_input`, **streamelés** `st.write_stream`-mel a backend agent-válaszából.
- Agent-válasz: **beszédpontok + forrás-chipek** (⤴), nem szó szerinti script; groundedness-jelzés.
- Oldalsó panel: hivatkozott források (`source_card`).
- **Telefon mód**: hívásátirat beillesztése (szimulált feliratozás) → azonnali beszédpontok.
- **„Ügy létrehozása"** a beszélgetésből → átvált az ügy-munkaállomásra.

### 4.6 Postai levél import
- PDF feltöltés (`st.file_uploader`, drag & drop) → `/ocr` → **szerkeszthető OCR-előnézet** konfidencia-jelzéssel (alacsony konfidenciájú részek kiemelve) → „Feldolgozás" → ügy-munkaállomás.

### 4.7 Evaluation
- „Kiértékelés indítása" (`/eval/run`), opcionális szűrés kategóriára/szolgáltatóra.
- **KPI-kártyák** (`kpi_card`): érték + célérték + állapotszín (zöld/sárga/piros): source citation rate, kritikus hallucináció, coverage, escalation appropriateness, time-to-answer, version mismatch, audit completeness.
- Kérdés-szintű tábla (groundedness, citation flag, retrieval-support, judge-pontszám, emberi 1–5 mező).
- Regresszió (aktuális vs. baseline diff), riport export.

### 4.8 Supervisor (csak supervisor szerepkör)
- Eszkalált ügyek sora (ok, prioritás, SLA, átvétel).
- Aggregált statisztika-dashboard `kpi_card`-okkal (feldolgozott ügyek, eszkalációs arány, átlagos válaszidő, ÜI-visszajelzés) — **aggregált, nem egyedi PII**.

## 5. Komponens-leltár (`ui/components.py`)

Újrahasznosítható, One-tokenekre stílusozott komponensek; mindegyik egy dolgot csinál, jól definiált bemenettel:

| Komponens | Felelősség | Bemenet (kb.) |
|---|---|---|
| `top_header` | fejléc-sáv (logó, kereső, chipek, user) | user, aszf_version, provider |
| `icon_nav` | szerepkör-függő ikon-navigáció | role, aktív elem → kiválasztott nézet |
| `badge` | színkódolt címke | típus (kategória/prioritás/konf/eszkaláció/SLA/csatorna), érték |
| `source_card` | forrás-kártya | §, dok_tipus, idézet, magyarázat, ugrólink |
| `history_card` | előzmény-kártya | dátum, tárgy, kategória, státusz |
| `customer_card` | ügyféltörzs-kártya | név, azonosító, kiválasztó |
| `agent_step` | idővonal-lépés | név, állapot, kibontható kimenet |
| `draft_editor` | draft szerkesztő blokk | draft, verziók, mód, citationök, callbackek |
| `kpi_card` | KPI-kártya | érték, célérték, állapotszín |
| `chat_turn` | chat-buborék beszédpontokkal/forrás-chipekkel | szerep, tartalom, források |

## 6. Adatfolyam

A UI **prezentációs réteg marad** — minden adat a meglévő `ui/api_client.py`-on át a FastAPI backendből jön. **Nincs új végpont.** Használt endpointok: `/health`, `login`, `/reindex`, `/inbox`, `/cases/{id}`, `/cases/process`, `/cases/draft`, `/cases/approve`, `/cases/feedback`, `/cases/status`, `/agent/run`, `/ocr`, `/eval/run`, `/eval/runs/{id}`, `/eval/baseline`, `/eval/human-score`, `/supervisor/*`, `/audit/*`, `/customer-lookup`, `/history`.

Minden válasz hordozza: `request_id`, `model_profile`, `prompt_version`, `aszf_version` — ezeket a fejléc/diagnosztika kijelzi.

## 7. Állapotok és élfeltételek
- **Betöltés:** agent-lépéseknél `⟳` + `st.status`/spinner; lépések inkrementálisan jelennek meg, streamelve.
- **Hiba:** node-hiba `✗` + hibaüzenet; retry. Backend elérhetetlen → fejléc alatti „Backend offline" banner.
- **Eszkaláció:** eszkalált ügy a középső műveletek helyett „supervisorhoz eszkalálva" állapotot mutat.
- **Üres állapotok:** inbox/előzmény/ügyféltörzs „nincs adat".
- **Hatókörön kívül:** draft helyett „nincs elég információ + eszkaláció javasolt".

## 8. Hozzáférés-vezérlés (RBAC) a UI-ban
- Maszkolatlan PII / unmask csak jogosult szerepkörnek; az „Jóváhagyom kiküldésre" előtti unmask naplózva (backend-logika változatlan).
- Supervisor statisztika aggregált (nem egyedi PII).
- A supervisor menüpont csak supervisor szerepkörnek látszik.

## 9. Tesztelés
- **Nézet-smoke-tesztek** `streamlit.testing.v1.AppTest`-tel: minden nézet betölt hiba nélkül mockolt `api_client` mellett.
- **Komponens-render ellenőrzés:** `badge`, `source_card`, `kpi_card` stb. hibamentesen renderel jellemző bemenetekre.
- `api_client` hívások mockolva; nincs valódi backend a UI-tesztekhez.
- POC-szint: a cél a regressziómentes átöltöztetés, nem a teljes lefedettség.

## 10. Megvalósítási megjegyzések / korlátok
- A háromhasábos elrendezés `st.columns([1,2,1])`; panelek kártyákban/expanderben.
- Az idővonal inkrementális frissítése `st.status`/`st.empty` + rerun-minta.
- Kiemelés/hover/chipek egyszerű HTML/markdown (`unsafe_allow_html=True`); komplex interakcióhoz opcionális egyedi komponens.
- Új függőség (opcionális): `streamlit-option-menu` az ikon-navigációhoz — ha nem kívánatos, CSS-ezett `st.radio` a fallback.
- A pontos One türkiz hex egy helyen (`ui/theme.py` + `config.toml`) cserélhető, ha rendelkezésre áll a márkakönyvi kód.
