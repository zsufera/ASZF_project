# Vizuális és UX modernizáció — Implementációs terv

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A frontend UI-t hackathon-demó szintre emelni: modern vizuális megjelenés, logikus elrendezés, a termék "gondolkodásának" látványos bemutatása a zsűrinek.

**Architecture:** Kizárólag frontend (React + TS + Tailwind) módosítások. Nincs backend-változás. A `lucide-react` ikon-könyvtár az egyetlen új dependency. A meglévő One design tokeneket és CSS custom property-ket használjuk (`index.css`). A munkát 10 taskra bontjuk, amelyeket prioritási sorrendben érdemes végrehajtani — az elsők a legnagyobb hatásúak és legkisebb kockázatúak.

**Tech Stack:** React 18, TypeScript, Tailwind CSS 3, Vite 5, lucide-react (új)

---

## Kontextus a végrehajtónak

### Repo-struktúra
- `frontend/src/index.css` — design tokenek (CSS custom properties)
- `frontend/src/components/` — újrahasználható komponensek
- `frontend/src/screens/` — oldalak (Inbox, CaseWorkstation, Copilot, stb.)
- `frontend/src/lib/agentSteps.ts` — pipeline step metaadatok
- `frontend/tailwind.config.js` — Tailwind konfig One design tokenekkel

### Futtatás
```powershell
cd frontend; npm install; npm run dev      # localhost:5173, belépés: ui_demo / ui_demo
npx tsc --noEmit                           # típusellenőrzés
npm run build                              # build ellenőrzés
```

### Fontos szabályok
- **PowerShell:** nincs `&&` — használj `;` vagy külön parancsokat
- **Commitolj gyakran**, kis lépésekben, ágon (ne main-re). Trailer: `Co-Authored-By: Claude ...`
- **Named exportok** mindenhol
- **Ékezetes magyar** feliratok kötelezők a UI-on
- Típusellenőrzés (`tsc --noEmit`) és build (`npm run build`) legyen tiszta minden task után

---

## Task 1: Lucide ikonok — emoji-csere az egész app-ban

Ez az egyetlen legnagyobb vizuális ugrás. Az emoji ikonok OS-függők, nem színezhetők, és amatőr benyomást keltenek. A `lucide-react` vékony vonalas SVG ikonok modernek, és aktív állapotban a One türkiz színre váltanak.

**Files:**
- Modify: `frontend/package.json` (dependency hozzáadása)
- Modify: `frontend/src/components/IconNav.tsx` (navigációs ikonok)
- Modify: `frontend/src/components/TopHeader.tsx` (fejléc ikonok)
- Modify: `frontend/src/components/Badge.tsx` (badge ikonok)

- [ ] **Step 1: Telepítsd a lucide-react csomagot**

```bash
cd frontend && npm install lucide-react
```

Ellenőrzés: `package.json`-ban megjelent a `"lucide-react"` a dependencies-ben.

- [ ] **Step 2: Cseréld le az IconNav emoji ikonjait lucide SVG ikonokra**

A `frontend/src/components/IconNav.tsx` fájlban:

1. Importáld a szükséges ikonokat:
```tsx
import { Inbox, PenSquare, MessageCircle, Mail, BarChart3, BookOpen, Shield } from "lucide-react";
```

2. A `NAV_ITEMS` tömb `icon` mezőjét cseréld `React.ComponentType`-ra. Így nézzen ki az egész fájl:

```tsx
import { NavLink } from "react-router-dom";
import { Inbox as InboxIcon, PenSquare, MessageCircle, Mail, BarChart3, BookOpen, Shield } from "lucide-react";
import type { Role } from "../lib/types";
import type { ComponentType } from "react";

interface NavItem {
  to: string;
  icon: ComponentType<{ size?: number; className?: string }>;
  label: string;
  roles?: Role[];
}

const NAV_ITEMS: NavItem[] = [
  { to: "/inbox", icon: InboxIcon, label: "Inbox" },
  { to: "/new", icon: PenSquare, label: "Új ügy" },
  { to: "/copilot", icon: MessageCircle, label: "Copilot" },
  { to: "/postal", icon: Mail, label: "Postai levél" },
  { to: "/eval", icon: BarChart3, label: "Evaluation" },
  { to: "/knowledge", icon: BookOpen, label: "Tudás" },
  { to: "/supervisor", icon: Shield, label: "Superv.", roles: ["supervisor"] },
];

export function IconNav({ role }: { role: Role }) {
  const items = NAV_ITEMS.filter((i) => !i.roles || i.roles.includes(role));
  return (
    <nav
      aria-label="Főnavigáció"
      className="w-[70px] bg-one-surface border-r border-one-line flex flex-col gap-1.5 py-3 items-center"
      style={{ minHeight: "calc(100vh - var(--header-h))" }}
    >
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          aria-current={undefined}
          className={({ isActive }) =>
            `w-[50px] h-[44px] rounded-xl flex flex-col items-center justify-center gap-0.5 text-[9px] transition-colors duration-100 ${
              isActive
                ? "bg-one-turq-l text-one-turq-d font-semibold"
                : "text-one-grey hover:bg-one-canvas"
            }`
          }
          aria-label={item.label}
        >
          {({ isActive }) => (
            <>
              <item.icon
                size={18}
                className={isActive ? "text-one-turq-d" : "text-one-grey"}
                aria-hidden="true"
              />
              <span>{item.label}</span>
              {isActive && <span className="sr-only">(aktív)</span>}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
```

- [ ] **Step 3: Cseréld le a TopHeader emoji ikonjait**

A `frontend/src/components/TopHeader.tsx` fájlban:

1. Add hozzá az importot:
```tsx
import { Cloud, Server, User, LogOut, AlertTriangle } from "lucide-react";
```

2. Cseréld az alábbi emoji-kat a fejlécben:
   - `"⚠ Offline"` → `<AlertTriangle size={12} className="inline" /> Offline`
   - `"☁ Felhő"` → `<Cloud size={12} className="inline mr-1" />Felhő`
   - `"🖥 On-prem"` → `<Server size={12} className="inline mr-1" />On-prem`
   - `"👤 {user.username}"` → `<User size={12} className="inline mr-1" />{user.username}`
   - A "Kilép" gomb szövege marad, de opcionálisan: `<LogOut size={10} className="inline mr-1" />Kilép`

- [ ] **Step 4: Cseréld le a Badge.tsx emoji-kat**

A `frontend/src/components/Badge.tsx` fájlban:

1. Importok:
```tsx
import { AlertCircle, AlertTriangle, Clock } from "lucide-react";
```

2. Cserék:
   - `"● {value}"` (priority badge) → `<AlertCircle size={10} className="inline mr-0.5" />{value}`
   - `"⚠ {value}"` (escalation badge) → `<AlertTriangle size={10} className="inline mr-0.5" />{value}`
   - `"⏱ {value} nap"` (SLA badge) → `<Clock size={10} className="inline mr-0.5" />{value} nap`

- [ ] **Step 5: Ellenőrzés és commit**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

Ha tiszta:
```bash
git add frontend/package.json frontend/package-lock.json frontend/src/components/IconNav.tsx frontend/src/components/TopHeader.tsx frontend/src/components/Badge.tsx
git commit -m "feat(ui): replace emoji icons with lucide-react SVGs across nav, header, badges"
```

---

## Task 2: Ékezethiányos feliratok javítása

A case-oldal és több más képernyő ASCII-only feliratokat használ (pl. "FORRASOK", "BEJOVO UZENET", "Jovahagyott tartalom"). Magyar zsűrinél ez azonnal szemet szúr.

**Files:**
- Modify: `frontend/src/components/case/CaseSourcesPanel.tsx`
- Modify: `frontend/src/components/case/CaseDraftPanel.tsx`
- Modify: `frontend/src/components/case/CaseInboundMessage.tsx`
- Modify: `frontend/src/components/case/CaseHistoryPanel.tsx`
- Modify: `frontend/src/components/case/CaseCustomerPanel.tsx`
- Modify: `frontend/src/components/case/CaseTimelinePanel.tsx`
- Modify: `frontend/src/components/case/AuditPanel.tsx`
- Modify: `frontend/src/components/DraftEditor.tsx`
- Modify: `frontend/src/screens/CaseWorkstation.tsx`
- Modify: `frontend/src/screens/Knowledge.tsx`

- [ ] **Step 1: Keresd meg az összes ékezet nélküli feliratot**

Futtasd:
```bash
cd frontend && npx grep -rn "Forrasok\|Bejovo\|Elozmenyek\|Ugyfeltorzs\|Betoltes\|Jovahagyott\|Kuldesre\|Jovahagyom\|Jovahagyás\|feldolgozas\|inditasa\|Targy\|Uzenet\|ujrafutt" src/ --include="*.tsx"
```

A cserék listája (minden fájlban keresd meg és cseréld az alábbi stringeket):

| Jelenlegi | Helyes |
|---|---|
| `"Forrasok"` | `"Források"` |
| `"Bejovo uzenet"` / `"BEJOVO UZENET"` | `"Bejövő üzenet"` / `"BEJÖVŐ ÜZENET"` |
| `"Elozmenyek"` | `"Előzmények"` |
| `"Ugyfeltorzs-jeloltek"` | `"Ügyféltörzs-jelöltek"` |
| `"Betoltes..."` | `"Betöltés…"` |
| `"Jovahagyott tartalom - Kuldesre kesz"` | `"Jóváhagyott tartalom — Küldésre kész"` |
| `"Jovahagyom kikuldesre"` | `"Jóváhagyom kiküldésre"` |
| `"Kuldes megerositese"` | `"Küldés megerősítése"` |
| `"Level kikuldve!"` | `"Levél kiküldve!"` |
| `"Feldolgozas inditasa"` | `"Feldolgozás indítása"` |
| `"Feldolgozas ujra"` / `"Feldolgozas..."` | `"Feldolgozás újra"` / `"Feldolgozás…"` |
| `"Draft mentese"` | `"Draft mentése"` |
| `"Agent feldolgozas inditasa"` | `"Agent feldolgozás indítása"` |
| `"Agent feldolgozas ujrafuttatasa"` | `"Agent feldolgozás újrafuttatása"` |
| `"Valassz egy ASZF szakaszt."` | `"Válassz egy ÁSZF-szakaszt."` |

Fontos: az `aria-label` attribútumoknál is cseréld le, ha ékezet nélküli!

- [ ] **Step 2: Ellenőrzés és commit**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

```bash
git add -u frontend/src/
git commit -m "fix(ui): add proper Hungarian diacritics to all UI labels"
```

---

## Task 3: Halott funkciók eltávolítása a case-oldalról

Három elem van a DraftEditor-ban, ami nem működik, félrevezető, vagy a demó fő üzenetét ássa alá.

**Files:**
- Modify: `frontend/src/components/DraftEditor.tsx`

- [ ] **Step 1: Távolítsd el a "Szabad szöveg / Sablonblokkok" váltót**

A `frontend/src/components/DraftEditor.tsx` fájlban:
1. Töröld a `mode` state-et: `const [mode, setMode] = useState<"free" | "template">("free");`
2. Töröld a teljes `<div className="flex border border-one-line rounded-md overflow-hidden text-[10px]">` blokkot ami a "Szabad szöveg" és "Sablonblokkok" gombokat tartalmazza (a 96–109. sor körül).

- [ ] **Step 2: Távolítsd el a "HITL / Automata" kapcsolót**

Ugyanebben a fájlban:
1. Töröld a `<div className="ml-auto flex border border-one-line rounded-md overflow-hidden text-[10px]">` blokkot ami a "HITL" és "Automata" gombokat tartalmazza (128–141. sor körül).
2. Távolítsd el az `onModeChange` propot és az `outputMode` propot a `DraftEditorProps` interfészből.
3. A `DraftEditor` függvény paraméterlistájából is vedd ki ezeket.

**A hívó oldalon is tisztítani kell:**
- `frontend/src/components/case/CaseDraftPanel.tsx`: vedd ki az `outputMode` és `onModeChange` propokat a `CaseDraftPanelProps`-ból és a továbbadásból.
- `frontend/src/screens/CaseWorkstation.tsx`: vedd ki az `outputMode` és `onModeChange` átadását a `<CaseDraftPanel>`-nak. Az `outputMode` state a `useSession`-ből maradhat (a backend használja), de a UI-ból eltűnik a kapcsoló.

- [ ] **Step 3: Ellenőrzés és commit**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

```bash
git add -u frontend/src/
git commit -m "fix(ui): remove non-functional template toggle and HITL/Automata switch from draft editor"
```

---

## Task 4: Döntési összefoglaló kártya a case-oldalra

A zsűri számára a legfontosabb, hogy egy pillantásra lássa, mit "gondol" a rendszer az ügyről. Ez az információ most a 12 lépéses idővonalba van eltemetve. Egy hero-kártya kell a bejövő üzenet fölé.

**Files:**
- Create: `frontend/src/components/case/CaseDecisionSummary.tsx`
- Modify: `frontend/src/screens/CaseWorkstation.tsx`

- [ ] **Step 1: Hozd létre a CaseDecisionSummary komponenst**

Új fájl: `frontend/src/components/case/CaseDecisionSummary.tsx`

```tsx
import { AlertTriangle, CheckCircle, Shield, Search, Tag, Zap } from "lucide-react";
import type { Case } from "../../lib/types";

interface CaseDecisionSummaryProps {
  caseData: Case;
}

export function CaseDecisionSummary({ caseData }: CaseDecisionSummaryProps) {
  const agentState = caseData.agent_state;
  if (!agentState?.timeline?.length) return null;

  const classification = agentState.classification;
  const escalation = agentState.escalation;
  const retrieval = agentState.retrieval;
  const draft = agentState.draft;
  const priority = agentState.priority;

  const category = classification?.category ?? "—";
  const confidence = classification?.confidence;
  const confidencePercent = confidence != null ? Math.round(confidence * 100) : null;
  const confidenceColor =
    confidence != null && confidence >= 0.8
      ? "text-kpi-ok"
      : confidence != null && confidence >= 0.6
        ? "text-kpi-warn"
        : "text-kpi-bad";

  const priorityValue = priority?.value ?? "normál";
  const isUrgent = priorityValue === "surgos";

  const escalationRequired = escalation?.required ?? false;
  const escalationReasons = escalation?.reasons ?? [];

  const sourceCount = retrieval?.chunks?.length ?? 0;
  const generationMode = draft?.generation_mode;
  const hasEnoughCoverage = generationMode !== "insufficient";

  return (
    <div className="bg-one-surface border border-one-line rounded-[var(--r-lg)] shadow-card p-4 mb-3">
      <div className="text-[10px] uppercase text-one-grey tracking-wider font-semibold mb-3">
        Döntési összefoglaló
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <SummaryChip
          icon={Tag}
          label="Kategória"
          value={category}
          detail={confidencePercent != null ? `${confidencePercent}% konfidencia` : undefined}
          detailColor={confidenceColor}
        />
        <SummaryChip
          icon={Zap}
          label="Prioritás"
          value={isUrgent ? "SÜRGŐS" : "Normál"}
          valueColor={isUrgent ? "text-status-urgent-fg" : undefined}
          detail={priority?.reason}
        />
        <SummaryChip
          icon={Shield}
          label="Eszkaláció"
          value={escalationRequired ? "Szükséges" : "Nem szükséges"}
          valueColor={escalationRequired ? "text-status-esc-fg" : "text-kpi-ok"}
          detail={escalationReasons.length ? escalationReasons.join(", ") : undefined}
        />
        <SummaryChip
          icon={Search}
          label="ÁSZF-fedezet"
          value={hasEnoughCoverage ? `${sourceCount} forrás` : "Nincs elég fedezet"}
          valueColor={hasEnoughCoverage ? "text-kpi-ok" : "text-status-esc-fg"}
          detail={hasEnoughCoverage ? undefined : "Emberi ellenőrzés javasolt"}
        />
      </div>
    </div>
  );
}

function SummaryChip({
  icon: Icon,
  label,
  value,
  valueColor,
  detail,
  detailColor,
}: {
  icon: typeof Tag;
  label: string;
  value: string;
  valueColor?: string;
  detail?: string;
  detailColor?: string;
}) {
  return (
    <div className="flex items-start gap-2">
      <Icon size={16} className="text-one-turq-d mt-0.5 flex-none" aria-hidden="true" />
      <div className="min-w-0">
        <div className="text-[9px] text-one-grey uppercase tracking-wider">{label}</div>
        <div className={`text-[12px] font-semibold ${valueColor ?? "text-one-ink"}`}>{value}</div>
        {detail && (
          <div className={`text-[10px] mt-0.5 truncate ${detailColor ?? "text-one-grey"}`}>{detail}</div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Illeszd be a CaseWorkstation-be**

A `frontend/src/screens/CaseWorkstation.tsx` fájlban:

1. Importáld:
```tsx
import { CaseDecisionSummary } from "../components/case/CaseDecisionSummary";
```

2. A CaseHeader után, a grid előtt illeszd be:
```tsx
<CaseDecisionSummary caseData={caseData} />
```

Tehát a struktúra:
```tsx
<CaseHeader ... />
<CaseDecisionSummary caseData={caseData} />
<div className={`grid gap-3 ...`}>
```

- [ ] **Step 3: Ellenőrizd, hogy a típusok illeszkednek**

A `CaseDecisionSummary` az `agentState.classification`, `.escalation`, `.retrieval`, `.priority`, `.draft` mezőket olvassa. Ellenőrizd, hogy a `Case` típusban (lásd `frontend/src/lib/types.ts`) ezek léteznek. Ha a `priority` nincs definiálva az `agent_state`-ben, adj hozzá egy opcionális mezőt:
```ts
priority?: { value: string; reason?: string };
```

Hasonlóan, ha a `classification` hiányzik:
```ts
classification?: { category: string; confidence?: number; subtype?: string };
```

- [ ] **Step 4: Ellenőrzés és commit**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

```bash
git add frontend/src/components/case/CaseDecisionSummary.tsx frontend/src/screens/CaseWorkstation.tsx frontend/src/lib/types.ts
git commit -m "feat(ui): add decision summary hero card to case workstation"
```

---

## Task 5: Case fejléc átszervezése — tárgy legyen a cím

Jelenleg a case fejléc a nyers technikai ID-t mutatja címként (pl. "Ugy #CASE-email-edge-005-nem-panasz"). A tárgy (subject) legyen az elsődleges cím, az ID másodlagos meta.

**Files:**
- Modify: `frontend/src/components/case/CaseHeader.tsx`

- [ ] **Step 1: Olvasd el a jelenlegi CaseHeader.tsx-et**

Nézd meg a meglévő struktúrát: milyen propokat kap, hogyan rendereli a case_id-t és a subject-et.

- [ ] **Step 2: Módosítsd a fejlécet**

A fejléc elrendezése legyen:
1. Felső sor: "← Vissza az inboxhoz" link (már megvan)
2. Fő sor:
   - Bal oldalon: **tárgy** (subject) nagy betűmérettel (`text-[18px] font-bold`), alatta a case_id halvány kisméretű szövegként (`text-[11px] text-one-grey font-mono`)
   - Mellette: kategória badge (`Badge` komponenssel)
   - Jobb oldalon: csatorna + SLA info (ami most is ott van)

A konkrét kód attól függ, mit találsz a jelenlegi `CaseHeader.tsx`-ben — a lényeg:
- A `<h1>` szövege legyen a `caseData.agent_state?.draft?.subject ?? caseData.subject ?? caseData.case_id`
- Az ID legyen alatta apró betűs, másolható (kattintásra clipboard)

- [ ] **Step 3: Ellenőrzés és commit**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

```bash
git add frontend/src/components/case/CaseHeader.tsx
git commit -m "feat(ui): show case subject as primary title, demote case ID to secondary"
```

---

## Task 6: Draft panel egyszerűsítése — duplikáció és segédkártyák eltávolítása

A draft panelen három probléma van:
1. A "Fedezet-előnézet" (InlineAnswer) és a szerkesztő ugyanazt a szöveget mutatja kétszer
2. A három segédkártya (Citation beszúrás, Jóváhagyási checklist, Verzió-diff) a fő gombokat a hajtás alá tolja
3. A "Jóváhagyom" gombot a checklist eredménye kell kapuzza

**Files:**
- Modify: `frontend/src/components/DraftEditor.tsx`
- Modify: `frontend/src/components/case/CaseDraftPanel.tsx`

- [ ] **Step 1: Töröld a "Fedezet-előnézet" blokkot a CaseDraftPanel-ből**

A `frontend/src/components/case/CaseDraftPanel.tsx` fájlban töröld a teljes `{draft.body_masked ? ( ... ) : null}` blokkot ami az `<InlineAnswer>` komponenst tartalmazza a "Fedezet-elonezet" felirat alatt (93–109. sor körül). Az `InlineAnswer` importot is távolítsd el, ha máshol nem használja a fájl.

- [ ] **Step 2: A három segédkártyát alakítsd át a DraftEditor-ban**

A `frontend/src/components/DraftEditor.tsx` fájlban:

**A) Citation-beszúrás kártya → eltávolítás:**
A `CitationInsertMenu` komponenst és a hozzá tartozó `<div className="grid grid-cols-3 ...">` teljes grid blokkot (179–183. sor körül) távolítsd el. A citation-beszúrás funkció a forráskártyákon lesz majd (külön task, de most a halott kártyát kivesszük).

**B) Jóváhagyási checklist → gombba olvasztás:**
A `ApprovalChecklist` komponenst szintén kiszeded a grid-ből, de a logikáját beolvasztod a "Jóváhagyom" gombba:

```tsx
const approvalReady = subject.trim().length > 0 && body.trim().length > 0 && Boolean(selectedVersion);
```

A "Jóváhagyom" gomb kapja meg a `disabled` feltételt:
```tsx
disabled={approving || !approvalReady}
```

És ha `!approvalReady`, a gomb kapjon egy `title` attribútumot:
```tsx
title={!approvalReady ? "Tárgy, szöveg és verzió szükséges" : undefined}
```

**C) Verzió-diff → lenyitható, csak ha van 2+ verzió:**
A `DraftVersionDiff` komponenst hagyd meg, de ne a gridben, hanem a verzióválasztó mellé tedd egy kis "Diff" gombbal lenyithatóvá, közvetlenül a verzió-select után:

```tsx
const [showDiff, setShowDiff] = useState(false);

// A verzió-select mellett:
{versions.length >= 2 && (
  <button
    onClick={() => setShowDiff((v) => !v)}
    className="text-[10px] text-one-turq-d hover:underline"
  >
    {showDiff ? "Diff elrejtése" : "Diff"}
  </button>
)}

// Alatta, a subject input előtt:
{showDiff && versions.length >= 2 && (
  <DraftVersionDiff currentBody={body} previousBody={previousVersion?.body_masked ?? ""} previousLabel={previousVersion ? `v${previousVersion.version_no}` : "előző"} />
)}
```

- [ ] **Step 3: Töröld a felesleges kódot**

Távolítsd el a `CitationInsertMenu` és `ApprovalChecklist` lokális function-öket a fájl aljáról (de `DraftVersionDiff` marad).

- [ ] **Step 4: Ellenőrzés és commit**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

```bash
git add -u frontend/src/
git commit -m "refactor(ui): simplify draft panel — remove duplicate preview, inline approval check into button"
```

---

## Task 7: Skeleton loader és üres állapotok

A "Betöltés…" szöveg és az üres fehér felületek (Copilot, Postai levél, Inbox) modernizálása.

**Files:**
- Create: `frontend/src/components/Skeleton.tsx`
- Modify: `frontend/src/screens/Inbox.tsx`
- Modify: `frontend/src/screens/Copilot.tsx`
- Modify: `frontend/src/screens/Postal.tsx`

- [ ] **Step 1: Hozd létre a Skeleton komponenst**

Új fájl: `frontend/src/components/Skeleton.tsx`

```tsx
export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-md bg-one-line ${className}`}
      aria-hidden="true"
    />
  );
}

export function InboxSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="bg-one-surface border border-one-line rounded-[var(--r-md)] shadow-card p-3 flex items-start gap-3">
          <div className="flex-1 space-y-2">
            <div className="flex gap-1">
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-12" />
              <Skeleton className="h-4 w-14" />
            </div>
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
          <Skeleton className="h-7 w-20 rounded-full" />
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Használd az InboxSkeleton-t az Inbox-ban**

A `frontend/src/screens/Inbox.tsx` fájlban:

1. Importáld:
```tsx
import { InboxSkeleton } from "../components/Skeleton";
```

2. Cseréld le:
```tsx
{loading && <div className="text-one-grey text-[12px]">Betöltés...</div>}
```
Erre:
```tsx
{loading && <InboxSkeleton />}
```

- [ ] **Step 3: Üres állapot illusztráció a Copilot chat-hez**

A `frontend/src/screens/Copilot.tsx` fájlban cseréld le az üres állapot szöveget (237. sor körül):

```tsx
{messages.length === 0 && (
  <p className="text-one-grey text-[12px] text-center pt-8">Írj üzenetet a copilotnak…</p>
)}
```

Erre:
```tsx
{messages.length === 0 && (
  <div className="flex flex-col items-center justify-center pt-16 text-center">
    <MessageCircle size={40} className="text-one-line mb-3" />
    <p className="text-[13px] font-semibold text-one-ink mb-1">Kérdezz az ÁSZF-ről</p>
    <p className="text-[11px] text-one-grey max-w-xs">
      A copilot megkeresi a releváns szabályzati szakaszokat és forrásokra hivatkozó választ ad.
    </p>
  </div>
)}
```

Importáld a `MessageCircle`-t:
```tsx
import { MessageCircle } from "lucide-react";
```

- [ ] **Step 4: Üres állapot a Postai levél képernyőhöz**

A `frontend/src/screens/Postal.tsx` fájlban cseréld a drop-zone szövegét:

```tsx
<p className="text-one-grey text-[13px] mb-1">📮 Húzd ide a PDF fájlt, vagy kattints a feltöltéshez</p>
```

Erre (lucide ikonnal):
```tsx
<Mail size={32} className="text-one-line mb-2 mx-auto" />
<p className="text-one-grey text-[13px] mb-1">Húzd ide a PDF fájlt, vagy kattints a feltöltéshez</p>
```

Importáld a `Mail`-t:
```tsx
import { Mail } from "lucide-react";
```

- [ ] **Step 5: Ellenőrzés és commit**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

```bash
git add frontend/src/components/Skeleton.tsx frontend/src/screens/Inbox.tsx frontend/src/screens/Copilot.tsx frontend/src/screens/Postal.tsx
git commit -m "feat(ui): add skeleton loaders and illustrated empty states"
```

---

## Task 8: Inbox statisztika-fejléc (mini dashboard)

Az Inbox fejlécébe 4 KPI csempe: nyitott ügyek, sürgős, eszkalált, átlag SLA. A meglévő `KpiGrid` komponenst újrahasznosítjuk.

**Files:**
- Modify: `frontend/src/screens/Inbox.tsx`
- Modify: `frontend/src/lib/api.ts` (ha kell új endpoint)
- Modify: `frontend/src/lib/types.ts` (ha kell új típus)

- [ ] **Step 1: Számítsd ki a KPI-kat a meglévő inbox adatokból**

A `frontend/src/screens/Inbox.tsx` fájlban nincs szükség új API-hívásra — a már betöltött `items` tömbből mindent ki lehet számítani:

Az `Inbox` komponensben, az `items` state után add hozzá:

```tsx
import { KpiGrid } from "../components/KpiCard";
import type { KpiStatus } from "../lib/types";

// Az Inbox komponensen belül, a return előtt:
const inboxKpis = useMemo(() => {
  if (!items.length) return [];
  const open = items.filter((i) => i.status_label !== "Lezárt").length;
  const urgent = items.filter((i) => i.priority === "surgos").length;
  const escalated = items.filter((i) => i.escalated).length;
  const avgSla = items.length
    ? Math.round(items.reduce((sum, i) => sum + i.sla_days_remaining, 0) / items.length)
    : 0;
  return [
    { label: "Nyitott", value: open, status: (open > 10 ? "red" : open > 5 ? "yellow" : "green") as KpiStatus },
    { label: "Sürgős", value: urgent, status: (urgent > 0 ? "red" : "green") as KpiStatus },
    { label: "Eszkalált", value: escalated, status: (escalated > 3 ? "red" : escalated > 0 ? "yellow" : "green") as KpiStatus },
    { label: "Átl. SLA (nap)", value: avgSla, status: (avgSla < 3 ? "red" : avgSla < 7 ? "yellow" : "green") as KpiStatus },
  ];
}, [items]);
```

- [ ] **Step 2: Rendereld a KPI grid-et az Inbox fejlécébe**

A `<h1>` és a `<SavedViewsBar>` közé szúrd be:

```tsx
{!loading && inboxKpis.length > 0 && (
  <div className="mb-4">
    <KpiGrid items={inboxKpis} perRow={4} />
  </div>
)}
```

- [ ] **Step 3: Ellenőrzés és commit**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

```bash
git add frontend/src/screens/Inbox.tsx
git commit -m "feat(ui): add KPI summary cards to inbox header"
```

---

## Task 9: Mikro-interakciók és kártya-hover effektek

Enyhe emelkedés és árnyék hover-nél, gomb-nyomás animáció, stagger animáció a listáknál.

**Files:**
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/screens/Inbox.tsx`

- [ ] **Step 1: Bővítsd a CSS animációkat**

A `frontend/src/index.css` fájl végére add hozzá:

```css
@keyframes staggerFadeUp {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-stagger-fade-up {
  animation: staggerFadeUp 200ms ease-out both;
}

.hover-lift {
  transition: transform 120ms ease, box-shadow 120ms ease;
}
.hover-lift:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(14, 18, 18, 0.08);
}

.btn-press:active {
  transform: scale(0.97);
}
```

- [ ] **Step 2: Alkalmazd az Inbox kártyákon**

A `frontend/src/screens/Inbox.tsx` fájlban az inbox lista item-eknél:

1. A kártya `<div>` className-jéhez add hozzá: `hover-lift`
2. A "Megnyitás" gomb className-jéhez add hozzá: `btn-press`
3. Stagger animáció: a kártya `<div>`-hez adj `style` attribútumot:
```tsx
style={{ animationDelay: `${index * 30}ms` }}
```
És a className-hez add hozzá: `animate-stagger-fade-up`

- [ ] **Step 3: Alkalmazd a btn-press osztályt az összes elsődleges gombon**

Keresd meg az összes `bg-one-turq` gombot az app-ban, és adj hozzájuk `btn-press` osztályt. A legfontosabbak:
- `Inbox.tsx` — "Megnyitás" gomb
- `CaseDraftPanel.tsx` — "Feldolgozás indítása" gomb
- `DraftEditor.tsx` — "Jóváhagyom" gomb
- `Copilot.tsx` — "Küldés" gomb
- `Login.tsx` — "Belépés" gomb

- [ ] **Step 4: Ellenőrzés és commit**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

```bash
git add frontend/src/index.css frontend/src/screens/Inbox.tsx frontend/src/components/DraftEditor.tsx frontend/src/components/case/CaseDraftPanel.tsx frontend/src/screens/Copilot.tsx frontend/src/screens/Login.tsx
git commit -m "feat(ui): add hover-lift, btn-press, and stagger animations"
```

---

## Task 10: Agent pipeline vizuális stepper

Ez a demó differenciátora — a zsűrinek azt kell látnia, hogyan gondolkodik a rendszer. A jelenlegi `ProcessingIndicator` (szimulált vertikális lista) és az `AgentTimeline` (lenyitható szöveges lista) helyett egy vízszintes stepper szalag kerül a case fejléc alá.

**Files:**
- Create: `frontend/src/components/case/PipelineStepper.tsx`
- Modify: `frontend/src/screens/CaseWorkstation.tsx`
- Modify: `frontend/src/index.css` (stepper animáció)

- [ ] **Step 1: Adj hozzá CSS animációt az aktív step-nek**

A `frontend/src/index.css` végéhez:

```css
@keyframes pulseDot {
  0%, 100% { box-shadow: 0 0 0 0 rgba(22, 199, 192, 0.4); }
  50% { box-shadow: 0 0 0 6px rgba(22, 199, 192, 0); }
}

.pipeline-dot-active {
  animation: pulseDot 1.5s ease-in-out infinite;
}
```

- [ ] **Step 2: Hozd létre a PipelineStepper komponenst**

Új fájl: `frontend/src/components/case/PipelineStepper.tsx`

```tsx
import { useState } from "react";
import { CheckCircle, Circle, Loader } from "lucide-react";
import type { TimelineStep } from "../../lib/types";
import { stepLabel, STEP_META, fieldLabel, formatFieldValue } from "../../lib/agentSteps";

interface PipelineStepperProps {
  steps: TimelineStep[];
  processing?: boolean;
}

export function PipelineStepper({ steps, processing }: PipelineStepperProps) {
  const [hoveredStep, setHoveredStep] = useState<string | null>(null);

  if (!steps.length && !processing) return null;

  const completedSteps = new Set(steps.map((s) => s.step));

  return (
    <div className="mb-3">
      <div className="flex items-center gap-0 overflow-x-auto py-2 px-1">
        {steps.map((step, i) => {
          const meta = STEP_META[step.step];
          const isLast = i === steps.length - 1;
          const isActive = isLast && processing;

          return (
            <div key={step.step} className="flex items-center">
              <div
                className="relative flex flex-col items-center cursor-pointer"
                onMouseEnter={() => setHoveredStep(step.step)}
                onMouseLeave={() => setHoveredStep(null)}
              >
                <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                  isActive
                    ? "bg-one-turq pipeline-dot-active"
                    : "bg-one-turq"
                }`}>
                  {isActive ? (
                    <Loader size={12} className="text-white animate-spin" />
                  ) : (
                    <CheckCircle size={12} className="text-white" />
                  )}
                </div>
                <span className="text-[8px] text-one-grey mt-1 max-w-[60px] text-center truncate">
                  {meta?.label?.split(" ")[0] ?? step.step}
                </span>

                {hoveredStep === step.step && (
                  <div className="absolute top-8 left-1/2 -translate-x-1/2 z-20 bg-one-surface border border-one-line rounded-[var(--r-md)] shadow-card p-3 text-[10px] w-56 animate-fade-in">
                    <div className="font-semibold text-one-ink mb-1">{stepLabel(step.step)}</div>
                    {meta?.explain && <p className="text-one-grey mb-2">{meta.explain}</p>}
                    {step.output && (
                      <dl className="space-y-1">
                        {Object.entries(step.output).slice(0, 4).map(([key, value]) => (
                          <div key={key} className="flex justify-between gap-2">
                            <dt className="text-one-grey">{fieldLabel(key)}</dt>
                            <dd className="font-medium text-one-ink text-right">{formatFieldValue(key, value)}</dd>
                          </div>
                        ))}
                      </dl>
                    )}
                  </div>
                )}
              </div>
              {i < steps.length - 1 && (
                <div className="w-4 h-[2px] bg-one-turq mx-0.5 flex-none" />
              )}
            </div>
          );
        })}
        {processing && steps.length === 0 && (
          <div className="flex items-center gap-2 text-[11px] text-one-turq-d">
            <Loader size={14} className="animate-spin" />
            <span>Agent feldolgozás…</span>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Integráld a CaseWorkstation-be**

A `frontend/src/screens/CaseWorkstation.tsx` fájlban:

1. Importáld:
```tsx
import { PipelineStepper } from "../components/case/PipelineStepper";
```

2. A `<CaseDecisionSummary>` után (vagy ha azt nem csináltad még, a `<CaseHeader>` után), a grid előtt add hozzá:
```tsx
<PipelineStepper
  steps={caseData.agent_state?.timeline ?? []}
  processing={processing}
/>
```

3. Az idővonalat (jobb oldali `<CaseTimelinePanel>`) tedd opcionálissá: a grid `grid-cols-case-open` (3 oszlop) helyett legyen állandóan `grid-cols-case-closed` (2 oszlop), és a `<CaseTimelinePanel>` egy lenyitható panel legyen alul, nem oldalt. Egyszerűbb megoldás: hagyd meg a jelenlegi timeline-t, de állítsd `defaultOpen={false}`-ra, hogy alapból becsukva legyen, és a stepper vegye át a vizuális főszerepet.

A `CaseTimelinePanel`-nek való `onToggle` alapján a `timelineOpen` state határozza meg a grid-et. Módosítsd a `timelineOpen` alapértéket `false`-ra:
```tsx
const [timelineOpen, setTimelineOpen] = useState(false);
```

- [ ] **Step 4: Ellenőrzés és commit**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

```bash
git add frontend/src/components/case/PipelineStepper.tsx frontend/src/screens/CaseWorkstation.tsx frontend/src/index.css
git commit -m "feat(ui): add visual pipeline stepper with hover details to case workstation"
```

---

## Task összefoglaló és sorrend

| # | Task | Fájlok | Hatás | Kockázat |
|---|---|---|---|---|
| 1 | Lucide ikonok | 4 | Nagyon magas | Alacsony |
| 2 | Ékezetek javítása | ~10 | Magas | Nulla |
| 3 | Halott funkciók eltávolítása | 3 | Közepes | Alacsony |
| 4 | Döntési összefoglaló kártya | 2+1 új | Nagyon magas | Alacsony |
| 5 | Case fejléc átszervezés | 1 | Közepes | Alacsony |
| 6 | Draft panel egyszerűsítés | 2 | Magas | Közepes |
| 7 | Skeleton + üres állapotok | 3+1 új | Magas | Alacsony |
| 8 | Inbox KPI fejléc | 1 | Közepes | Alacsony |
| 9 | Mikro-interakciók | 5 | Közepes | Nulla |
| 10 | Pipeline stepper | 2+1 új | Nagyon magas | Közepes |

**Végrehajtási sorrend:** a számozás a javasolt sorrend. Az 1–3. task-ok gyors győzelmek (1–2 óra), a 4–6. a case-oldal áttervezése (2–3 óra), a 7–10. a végső polish (2–3 óra).

**Minden task után:** `npx tsc --noEmit && npm run build` + vizuális ellenőrzés böngészőben (a dev szerver `npm run dev`-vel fut a háttérben).
