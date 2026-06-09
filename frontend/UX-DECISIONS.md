# React UI — UX-döntések és eltérések a handofftól

Ez a React frontend az archivált [`docs/archive/design-export/design-handoff.md`](../docs/archive/design-export/design-handoff.md) alapján épül, az alábbi, tapasztalat-alapú finomításokkal. Cél: a Streamlit-korlátok nélkül logikusabb, gyorsabb felület — a megbeszélt arculat és IA megtartásával.

## Megtartva változatlanul
- One arculat (türkiz/fekete/fehér), tokenek a `docs/archive/design-export/tokens.css` / `tailwind.tokens.js`-ből.
- „Munkaállomás" IA: ikon-sáv + fejléc + főterület.
- Háromhasábos ügy-nézet (kontextus / draft / agent-idővonal).
- Postai levél önálló nav-pont; Copilot = Chat + Telefon.

## Finomítások (miért)
1. **Valódi útvonalak (react-router) a `viewMode` state helyett.** `/login`, `/inbox`, `/case/:id`, `/new`, `/copilot`, `/postal`, `/eval`, `/supervisor`. Így működik a böngésző vissza/előre gomb, és egy ügy **deep-linkelhető** (`/case/123`) — Streamlitben ez nem ment jól.
2. **Az idővonal becsukása ténylegesen újratördeli az elrendezést.** Nyitva `1fr 2fr 1fr`, becsukva `1fr 2.2fr` — a draft kapja a felszabaduló helyet (a handoff ezt kérte; Streamlit nem tudott reflow-zni). A választás `localStorage`-ban megmarad.
3. **A fejléc keresője valódi műveletet végez.** Pontos ügy-azonosító + Enter → `/case/:id`; egyébként → `/inbox` szűrés a kifejezésre.
4. **Toast visszajelzések** mentés/jóváhagyás/feedback után (nem tolják szét az elrendezést, mint az inline siker-üzenet).
5. **UI-preferenciák perzisztálása** (`modelProfile`, `outputMode`) és a bejelentkezett user `localStorage`-ban → túléli az újratöltést.
6. **A citation-chipek a megfelelő forrás-kártyára ugranak** (scroll + rövid kiemelés) — kereszt-link a draft és a források között.
7. **Unmask-előnézet modális dialógusban** (nem inline expander), tisztább és jobban jelzi az érzékeny műveletet.
8. **Robusztus offline-viselkedés:** ha a backend nem elérhető, az app betölt (login), és „Backend offline" banner + soronkénti hibakezelés jelenik meg; nincs fehér képernyő.
9. **a11y:** token-alapú fókuszgyűrű, `aria-current` az aktív nav-elemen, az idővonal-lépések valódi `button`-ök `aria-expanded`-del, az emoji- k mellett szöveges címke.

## Szándékosan kihagyva (YAGNI / POC)
- Külön komponens-könyvtár (shadcn stb.) — Tailwind utility-k elegendők, kisebb függőség.
- Automata teszt-suite — a Streamlit-oldali tesztek megvannak; itt a cél a működő, építhető SPA (alacsony költség).
- Token cseréje: a `#16C7C0` türkiz egy helyen cserélhető, ha jön a hivatalos One márkakód.

## Ismert korlátok (követendő)
- **Streamelés szimulált:** a chat soronként jeleníti meg az agent-választ (a `/agent/run` egyetlen JSON-t ad vissza, nincs SSE). Valódi token-stream backend-oldali SSE-vel pótolható.
- **Bejövő `<mark>` kiemelés:** jelenleg a maszkolt bejövő szöveg kiemelés nélkül jelenik meg. A kiemeléshez a backendnek vissza kellene adnia a kiemelendő span-eket (vagy kliens-oldali idézet-illesztés a retrieval chunk-okból, ahogy a Streamlit POC tette). Követendő finomítás.
- **Copilot „létrehozott ügy" id:** `sessionStorage`-ban (fül-szintű), fül bezárásakor törlődik — chat-munkamenethez elfogadható.
