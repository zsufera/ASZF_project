# ÁSZF Q&A Copilot — Design Handoff (One Magyarország)

> **Cél:** keretrendszer-független átadás, hogy a felület a megbeszélt irányok szerint, **nem Streamlitben** (cél: React + Tailwind) megvalósítható legyen.
> **Tartalom:** arculat, információs architektúra, képernyőnkénti elrendezés + interakciók + állapotok, komponens-leltár props-okkal, reszponzivitás, a11y, motion.
> **Kísérő fájlok:** [`tokens.css`](tokens.css), [`tailwind.tokens.js`](tailwind.tokens.js), [`api-contract.md`](api-contract.md), [`mockups/`](mockups/) (kattintható HTML/CSS makettek).
> A `mockups/*.html` tiszta HTML+CSS — nyisd meg böngészőben vagy másold belőlük a stílust; ezek a vizuális igazság-forrás a megjelenéshez.

---

## 0. Termék egy bekezdésben
Belső **ügyintézői copilot** telekom ügyfélszolgálatra. Bejövő ügyfél-üzenetből (email / chat / telefon-átirat / postai PDF) az agent ÁSZF-forrásokra hivatkozó **válaszlevél-javaslatot** és **eszkalációs döntéstámogatást** ad. **Human-in-the-loop**, auditálható. A felhasználó (ügyintéző) órákig nézi → nyugodt, letisztult, hivatalos megjelenés a cél.

## 1. Arculat (One Magyarország)
Türkiz + fekete + fehér, kör alakú „one" logó, flat/rounded, ember-központú. **A türkiz csak kiemelés** (aktív elem, gomb, link, fókusz, idővonal-pötty, badge) — nem nagy felületen. Fehér vászon, fehér kártyák, finom keret. A fekete a **bejelentkezőn** és a logó-momentumban jelenik meg.

> A `#16C7C0` türkiz **közelítés**; ha van hivatalos One márkakód, cseréld a `tokens.css` / `tailwind.tokens.js` egyetlen helyén.

### Token-tábla (a teljes lista: `tokens.css`)
| Token | Érték | Használat |
|---|---|---|
| `--one-turq` | `#16C7C0` | elsődleges kiemelés: aktív nav, gomb, link, fókusz |
| `--one-turq-d` | `#0FA39D` | hover, sötét türkiz szöveg |
| `--one-turq-l` | `#E3FAF8` | halvány türkiz háttér (badge, fejléc-gradiens) |
| `--one-black` | `#0E1212` | bejelentkező / erős márkamomentum |
| `--one-ink` | `#16201F` | fő szöveg |
| `--one-grey` | `#6B7A79` | másodlagos szöveg, label |
| `--one-line` | `#E2EAE9` | keret, elválasztó |
| `--one-canvas` / `--one-surface` | `#F7FAF9` / `#FFF` | vászon / kártya |
| status (urgent/esc/conf) | piros/narancs/sárga fg+bg párok | badge-ek |
| `--kpi-ok/warn/bad` | `#22A06B`/`#E0A400`/`#D64545` | KPI-kártya felső sáv |
| `--highlight` | `#FFF3B0` | bejövő szöveg `<mark>` kiemelés |

Tipográfia: `Segoe UI`/system sans. Méretek 10–22px (lásd `--fs-*`). Sugár: kártya 12px, shell 14px, gomb/badge pill (20px). Térköz: 4px-skála.

---

## 2. Információs architektúra — „Munkaállomás" modell
Keskeny **ikon-sáv** (bal, `--rail-w` 70px) + **fejléc** (felül, `--header-h` 52px) + **főterület**. A főterület két állapotú: **lista** és **teljes szélességű ügy-munkaállomás**.

```
┌──────────────────────────────────────────────────────────────┐
│ [one] ÁSZF Copilot   🔍 keresés     ÁSZF v3.2 · ☁ Felhő · 👤  │  fejléc
├──────┬───────────────────────────────────────────────────────┤
│ 📥   │                                                        │
│ ✏️   │   FŐTERÜLET                                             │
│ 💬   │   (lista-nézet  VAGY  teljes ügy-munkaállomás)         │
│ 📊   │                                                        │
│ 🛡️   │                                                        │
└──────┴───────────────────────────────────────────────────────┘
```

- **Ikon-sáv menü (szerepkör-függő):** Inbox · Új ügy · Copilot · Postai levél · Evaluation · *(Supervisor — csak `role==="supervisor"`)*. Aktív elem türkiz háttérrel/szöveggel.
- **Fejléc:** „one" logó + „ÁSZF Copilot"; globális kereső (ügy-azonosító/feladó); ÁSZF-verzió chip; modell-profil kapcsoló (Felhő/On-prem); bejelentkezett user + szerepkör; (Kijelentkezés).
- **Nézet-mód (state):** lista → ügy kiválasztása → `viewMode="case"` + `activeCaseId`; **„← Vissza"** → `viewMode="list"`. Az ügy a lista helyett teljes szélességben jelenik meg (nem alatta).
- Makett: [`mockups/nav-shell.html`](mockups/nav-shell.html) (A = Munkaállomás a választott irány).

**React-megjegyzés:** `viewMode`/`activeCaseId` lehet route is — javaslat: `/inbox`, `/case/:id`, `/new`, `/copilot`, `/eval`, `/supervisor`. A „Vissza" = navigálás `/inbox`-ra. A globális arculat-állapot (modell-profil, user) context/store.

---

## 3. Képernyők

### 3.1 Bejelentkezés
- **Fekete márkamomentum**: középen nagy „one" logó (kör, türkiz keret), cím „ÁSZF Copilot — Bejelentkezés".
- Mezők: felhasználónév, jelszó; „Belépés". Hibás belépés → hibajelzés a form alatt.
- Sikeres belépés → a `role` határozza meg a menüt; a user neve auditba kerül.
- Állapotok: alap / hiba (`{error}` a válaszból) / folyamatban.

### 3.2 Inbox (lista)
- Szűrő-sor: **Kategória · Prioritás · Státusz · Csatorna · Rendezés** (select-ek) + **keresőmező**.
- Lista: minden ügy **kártyán** — bal: badge-sor (email szöveg rövid nézete, kategória, SÜRGŐS, konfidencia, ⚠ eszkaláció, csatorna, státusz) + tárgy + SLA-hátralévő; jobb: **„Megnyitás"** primary gomb → ügy-munkaállomás.
- Rendezés: prioritás / SLA / beérkezés. Üres állapot: „Nincs megjeleníthető üzenet."
- Adat: `GET /inbox` → `items[]` (lásd api-contract).

### 3.3 Ügy-munkaállomás (HERO) — háromhasábos
A fő munkafelület. Felül **ügyfejléc** (halvány türkiz gradiens kártya): `Ügy #<id>`, badge-ek (kategória/SÜRGŐS/konfidencia/⚠ eszkaláció), feladó (maszkolt), **SLA-számláló**. Grid: `--case-cols` = `1fr 2fr 1fr`.
- Makett: [`mockups/case-workstation.html`](mockups/case-workstation.html).

**Bal — Kontextus** (One-kártyák):
- **Források:** § + `dok_tipus` + **szó szerinti idézet**; „Közérthető magyarázat" kapcsoló; ⤴ ugrás a teljes szakaszra.
- **Előzmények:** azonos címről jött üzenetek (dátum, tárgy, kategória, státusz); **ismétlődő-panasz** jelzés ha `is_repeated`.
- **Ügyféltörzs-jelöltek:** név + azonosító, kiválasztó (a kiválasztás szolgáltatóra szűkíthet), ⤴ (POC: mock).

**Közép — Tartalom:**
- **Bejövő üzenet** a hivatkozandó részek **`<mark>` kiemelésével** (highlight token).
- **Draft-szerkesztő:** szabad szöveg ⇄ strukturált sablonblokk kapcsoló; **verziótörténet** legördülő (`v1, v2…`); **kimeneti mód** (HITL ⇄ automata); kattintható **citationök**; gombok: **„💾 Draft mentése"**, **„✓ Jóváhagyom kiküldésre"** (primary; unmask RBAC → mock küldés → „lezárva", unmask-előnézet); **ÜI-visszajelzés** (👍 / 👎 / „rossz forrás").

**Jobb — Agent-idővonal:**
- **Kinyitható/becsukható konténer, ALAPÉRTELMEZÉSBEN NYITVA.** Becsukva több hely jut a draftnak.
- Lépések (`language…verify`) állapot-ikonnal: ✓ kész / ⚠ figyelmeztetés / ⟳ fut / ✗ hiba. **Lépésre kattintva** kibomlik a node kimenete (osztályozás-jelöltek, szabályzat-elemek, eszkaláció oka, nem-megalapozott állítások).
- Eszkalációnál kiemelt jelzés + **„⚠ Eszkaláció supervisorhoz"** gomb (ha `escalation.required`).

**Agent még nem futott:** a az első két hasáb él **„Agent feldolgozás indítása"** primary gomb → agent idővonalon követhető a folyamat állása

### 3.4 Copilot (chat / telefon) — natív beszélgetés
- **Chat:** user/agent buborékok; beviteli mező alul; **streamelő** agent-válasz. Az agent **beszédpontokat + forrás-chipeket** ad (⤴), nem szó szerinti scriptet; groundedness-jelzés.
- **Telefon mód:** hívásátirat beilleszthető (szimulált feliratozás) → azonnali beszédpontok.
- **„↗ Ügy létrehozása ebből a beszélgetésből"** → ügy-munkaállomásra vált (perzisztáld a `case_id`-t, hogy a gomb a rerun/újrarender után is működjön).
- Makett: [`mockups/copilot-chat.html`](mockups/copilot-chat.html). Adat: `create_case` → `process_case` (vagy `/agent/run`).

### 3.5 Postai levél import
- PDF feltöltés (drag & drop) → `POST /ocr` → **szerkeszthető OCR-előnézet** + konfidencia-jelzés (alacsony konfidenciájú részek kiemelve) → „Feldolgozás" → ügy-munkaállomás.

### 3.6 Evaluation
- „Kiértékelés indítása" (`/eval/run`), szűrők (kategória, szolgáltató, edge esetek).
- **KPI-kártyák**: érték + **felső színsáv** állapot szerint (zöld/sárga/piros) a `kpis.status` alapján — faithfulness, citation support, judge score, coverage, eszkaláció, retrieval support, idő p95, out-of-scope.
- Kérdés-szintű tábla, regresszió (baseline diff), riport export, emberi 1–5 spot-check.

### 3.7 Supervisor (csak `role==="supervisor"`)
- Felül **KPI-kártyák** (összes ügy, eszkalált, lezárt, eszkalációs arány) — **aggregált, nem egyedi PII**.
- **Eszkalált sor** (ok, prioritás, SLA, tárgy). Audit-rekord betöltése ügy-azonosítóval; megőrzési purge (dry-run).

---

## 4. Komponens-leltár (keretrendszer-független, React-props javaslattal)
| Komponens | Variánsok / állapotok | Props (javaslat) | Megjegyzés |
|---|---|---|---|
| `AppShell` | — | `{ role, user, aszfVersion, provider, children }` | rail + header + főterület grid |
| `IconNav` | aktív/inaktív elem | `{ items: NavItem[], active, onSelect }` | szerepkör-függő elemek |
| `TopHeader` | backend offline banner | `{ user, role, aszfVersion, provider, onProviderChange, onSearch }` | logó + kereső + chipek |
| `Badge` | `category\|priority\|confidence\|escalation\|sla\|channel\|status` | `{ kind, value }` | színkódolt pill; lásd token-párok |
| `CaseBadgeRow` | — | `{ case }` | a fenti badge-ek sora egy ügyhöz |
| `Card` | cím opcionális | `{ title?, children }` | fehér, 12px sugár, finom keret |
| `SourceCard` | „közérthető" be/ki | `{ section, dokTipus, quote, explanation?, onJump }` | § idézet + ⤴ |
| `HistoryCard` | ismétlődő jelzés | `{ items, isRepeated }` | előzmények |
| `CustomerCandidate` | kiválasztott | `{ name, id, linkUrl, selected, onSelect }` | szolgáltatóra szűkít |
| `DraftEditor` | szabad ⇄ sablon, HITL ⇄ automata | `{ draft, versions, mode, onModeChange, onSave, onApprove, onFeedback }` | citationök kattinthatók |
| `AgentTimeline` | **collapsible, default OPEN** | `{ steps, defaultOpen=true }` | lépés-ikonok ✓/⚠/⟳/✗; lépés kibontható |
| `TimelineStep` | ✓/⚠/⟳/✗ | `{ step, status, output }` | kattintásra JSON-kimenet |
| `KpiCard` | `ok\|warn\|bad` | `{ label, value, status }` | felső 4px színsáv |
| `KpiGrid` | — | `{ items, perRow=4 }` | KPI-kártyák rácsban |
| `ChatTurn` | user / assistant | `{ role, content, sources? }` | beszédpontok + forrás-chip |
| `SourceChip` | — | `{ label, onJump }` | kis türkiz chip (⤴) |

---

## 5. Állapotok és élfeltételek (mindenhol egységesen)
- **Loading:** agent-lépéseknél folyamatjelző (⟳), lépések inkrementálisan; gombok letiltva futás közben.
- **Hiba:** node-hiba ✗ + üzenet + retry. **Backend offline:** fejléc alatti „Backend offline — az adatok nem tölthetők." banner.
- **Üres:** inbox/előzmény/ügyféltörzs/eszkalált-sor „nincs adat" üzenettel.
- **Eszkaláció:** eszkalált ügynél a középső műveletek helyett „supervisorhoz eszkalálva" állapot.
- **Hatókörön kívül:** draft helyett „nincs elég információ + eszkaláció javasolt".
- **PII/RBAC:** alapból a `*_masked` mezők; unmask csak jogosult szerepkörnek, naplózva; supervisor statisztika aggregált.

## 6. Reszponzivitás
| Breakpoint | Viselkedés |
|---|---|
| Desktop > 1024px | teljes háromhasábos ügy-nézet (`1fr 2fr 1fr`); rail + főterület |
| Tablet 768–1024px | a jobb hasáb (idővonal) **becsukva** alapból; bal+közép marad; rail ikon-only |
| Mobil < 768px | egyhasábos, a hasábok **fülekre/accordionra** esnek szét (Kontextus / Draft / Idővonal); rail → alsó vagy hamburger-nav |

> A három hasáb belső prioritása: **közép (draft) a legfontosabb** → szűkülő helyen az kapja a teret, a jobb idővonal csukódik először.

## 7. Motion (visszafogott)
| Elem | Trigger | Animáció | Időtartam | Easing |
|---|---|---|---|---|
| Idővonal / kártya expander | kattintás | magasság + opacitás | 150–200ms | ease-out |
| Nézet-váltás (lista↔ügy) | navigáció | finom fade/slide | 150ms | ease |
| Chat-buborék megjelenés | új üzenet | fade-in + 4px felfelé | 120ms | ease-out |
| Streamelő válasz | token/sor | szöveg fokozatos megjelenése | — | — |
| Gomb hover | hover | háttér türkiz→`turq-d` | 100ms | ease |

## 8. Akadálymentesség (a11y)
- **Fókusz-sorrend:** fejléc → rail → szűrők → lista/munkaállomás; modalokban csapdázott fókusz.
- **Fókusz-gyűrű:** `--shadow-focus` (türkiz), sosem `outline:none` pótlás nélkül.
- **ARIA:** rail = `nav` + `aria-current` az aktívra; idővonal-lépés = `button`/`aria-expanded`; badge-eknél értelmes szöveg (ne csak szín/emoji közvetítse a jelentést — pl. „SÜRGŐS" szó is legyen ott).
- **Billentyűzet:** minden gomb/expander Enter/Space-re; chat-input Enter=küldés, Shift+Enter=új sor.
- **Kontraszt:** a türkiz szövegként `--one-turq-d` (sötétebb) használandó olvashatóságért; nagy türkiz felület kerülendő.
- **Kép-/ikon-jelentés:** az emoji-ikonok mellé szöveges címke vagy `aria-label`.

## 9. Hatókörön kívül / megjegyzések
- A Streamlit-specifikus megoldások (st.* widgetek, rerun-modell) **nem** relevánsak az új stackben — ez a doc szándékosan keretrendszer-független. Ahol viselkedés-mintát írok (pl. „a gomb a rerun után is működjön"), az általános state-perzisztencia tanácsra fordítandó.
- Nincs új backend funkció: minden a meglévő végpontokra épül (`api-contract.md`).
- Chainlit nem cél; a chat natív komponensekkel megoldható.
