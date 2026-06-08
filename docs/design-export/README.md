# Design Export — ÁSZF Q&A Copilot (One arculat) → új frontend

Ez a mappa **önállóan** tartalmaz mindent, ami a felület megbeszélt vizuális/UX irányainak átviteléhez kell egy **másik repóba / threadbe**, **nem Streamlit** (cél: **React + Tailwind**) megvalósításhoz.

## Tartalom
| Fájl | Mire való |
|---|---|
| [`design-handoff.md`](design-handoff.md) | A fő, keretrendszer-független spec: arculat, IA, képernyőnkénti elrendezés + interakció + állapotok, komponens-leltár, reszponzivitás, a11y, motion. **Ezzel kezdj.** |
| [`tokens.css`](tokens.css) | One design tokenek CSS custom property-ként (drop a `:root`-ba). |
| [`tailwind.tokens.js`](tailwind.tokens.js) | Ugyanazok a tokenek Tailwind `theme.extend`-hez. |
| [`api-contract.md`](api-contract.md) | A meglévő FastAPI végpontok + válasz-mezők, amikre a frontend épít. |
| [`mockups/`](mockups/) | Tiszta **HTML/CSS makettek** (nav-shell, one-theme, case-workstation, copilot-chat). Nyisd meg böngészőben — ez a vizuális igazság-forrás. |

## Hogyan vidd át jól (ajánlott lépések)

1. **Másold ezt a mappát** az új repo branchébe (pl. `frontend/design-source/` vagy a repo gyökerébe `design-export/`). A `mockups/*.html` önállóan megnyitható.
2. **Tokenek bekötése:**
   - Tailwind: `const one = require("./design-export/tailwind.tokens.js");` → `theme: { extend: one.extend }`.
   - Globál CSS-be importáld a `tokens.css`-t (a CSS-változókat a komponensek és a Tailwind arbitrary értékek is használhatják, pl. `bg-[var(--one-canvas)]`).
   - Ha van **hivatalos One türkiz hex**, cseréld a `tokens.css` és `tailwind.tokens.js` egy-egy sorában.
3. **Bontsd a munkát** a `design-handoff.md` komponens-leltára szerint: először `AppShell` + `TopHeader` + `IconNav` (váz), majd az **ügy-munkaállomás** (hero, háromhasábos, alapból nyitott becsukható idővonal), utána Inbox, Copilot-chat, Eval/Supervisor.
4. **API:** a frontend a meglévő backendre épül — futtatva `GET /openapi.json` a mérvadó; az `api-contract.md` a gyors referencia.
5. **Új thread indítása:** kezdd a lenti kickoff-prompttal, és csatold/másold be a négy fájlt (handoff, tokens, api-contract) + a mockupokat.

## Bemásolható kickoff-prompt az új threadhez

> Új frontendet építek egy meglévő belső telekom-ügyfélszolgálati **ÁSZF Q&A copilothoz**, **React + Tailwind** stacken (a korábbi POC Streamlit volt, azt NEM viszem tovább). A felület a **One Magyarország** arculatát követi (türkiz/fekete/fehér), „Munkaállomás" IA-val: ikon-sáv + fejléc + főterület, ahol az ügy teljes szélességű háromhasábos munkaállomásként nyílik (kontextus / draft / agent-idővonal), az idővonal kinyitható-becsukható, alapból nyitva. A copilot natív chat (beszédpontok + forrás-chipek).
>
> Mellékelem a teljes design-handoffot, a design tokeneket (CSS + Tailwind) és a backend API-kontraktust. Kérlek:
> 1. olvasd be a `design-handoff.md`-t, `tokens.css`-t, `tailwind.tokens.js`-t és az `api-contract.md`-t,
> 2. nézd meg a `mockups/*.html` maketteket a megjelenésért,
> 3. javasolj egy komponens-/route-struktúrát React + Tailwindben,
> 4. majd kezdjük a vázzal (AppShell + TopHeader + IconNav), utána az ügy-munkaállomással.
>
> A backendet és az API-kontraktust nem változtatjuk; minden a meglévő végpontokra épül.

## Megjegyzés
- A `mockups/*.html` a brainstorm során készült, gyors vizuális makett (nem pixel-pontos végeredmény) — az elrendezést és a hangulatot adja, nem kötelező CSS.
- Ez az export **csak forrás/dokumentáció** — semmilyen futtatható alkalmazást nem tartalmaz.
