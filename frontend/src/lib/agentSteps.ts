export interface StepMeta {
  label: string;     // közérthető magyar cím
  explain: string;   // egymondatos magyarázat, mit csinál a lépés
  fields: string[];  // mely output-mezőket mutassuk, sorrendben
}

export const STEP_META: Record<string, StepMeta> = {
  detect_lang_type: {
    label: "Nyelv és típus felismerése",
    explain: "Megállapítja a beérkező üzenet nyelvét és típusát (panasz, köszönet vagy hatókörön kívüli kérés).",
    fields: ["nyelv", "tipus"],
  },
  mask_input: {
    label: "Személyes adatok maszkolása",
    explain: "A személyes adatokat (név, cím, telefonszám) tokenekre cseréli, hogy a modell ne lásson valódi személyes adatot.",
    fields: ["token_count"],
  },
  load_context: {
    label: "Előzmények és ügyfél betöltése",
    explain: "Betölti a feladó korábbi ügyeit és a lehetséges ügyfél-találatokat.",
    fields: ["history_loaded", "customer_count", "is_repeated"],
  },
  classify: {
    label: "Ügy osztályozása",
    explain: "Kategóriába sorolja az ügyet, és megbecsüli, mennyire biztos a besorolásban (konfidencia).",
    fields: ["category", "confidence", "subtype", "is_repeated"],
  },
  priority_triage: {
    label: "Prioritás meghatározása",
    explain: "Eldönti, hogy az ügy sürgős-e, és megindokolja.",
    fields: ["value", "reason"],
  },
  retrieve: {
    label: "ÁSZF-források keresése",
    explain: "Megkeresi a kérdéshez kapcsolódó ÁSZF-szakaszokat.",
    fields: ["result_count"],
  },
  policy_map: {
    label: "Szabályzati megfeleltetés",
    explain: "A talált forrásokat a kategóriához tartozó kötelező hivatkozásokhoz illeszti.",
    fields: ["item_count"],
  },
  escalation: {
    label: "Eszkaláció vizsgálata",
    explain: "Eldönti, kell-e emberi (supervisor) felülvizsgálat, és megadja az okokat.",
    fields: ["required", "reasons"],
  },
  suggest_actions: {
    label: "Javasolt intézkedés",
    explain: "Megfogalmazza a javasolt lépést (tájékoztatás, eszkaláció vagy visszahívás).",
    fields: ["action_count"],
  },
  draft: {
    label: "Válaszjavaslat megfogalmazása",
    explain: "Megírja a forrásokra hivatkozó válasz- vagy levéljavaslatot.",
    fields: ["format", "source_count", "citation_count", "generation_mode"],
  },
  verify: {
    label: "Megalapozottság ellenőrzése",
    explain: "Ellenőrzi, hogy a válasz állításai a megadott forrásokon alapulnak-e.",
    fields: ["ungrounded_count"],
  },
  prepare_unmask: {
    label: "Jóváhagyásra előkészítés",
    explain: "Visszafejti a maszkolt adatokat a jóváhagyáshoz.",
    fields: ["ready_for_approval"],
  },
};

export const FIELD_LABELS: Record<string, string> = {
  nyelv: "Nyelv",
  tipus: "Típus",
  token_count: "Maszkolt tokenek",
  history_loaded: "Előzmény betöltve",
  customer_count: "Ügyfél-jelöltek",
  is_repeated: "Ismétlődő panasz",
  category: "Kategória",
  confidence: "Konfidencia",
  subtype: "Altípus",
  value: "Érték",
  reason: "Indok",
  result_count: "Találatok",
  item_count: "Szabályzati elemek",
  required: "Szükséges",
  reasons: "Okok",
  action_count: "Intézkedések",
  format: "Formátum",
  source_count: "Források",
  citation_count: "Hivatkozások",
  generation_mode: "Generálás módja",
  ungrounded_count: "Nem megalapozott állítások",
  ready_for_approval: "Jóváhagyásra kész",
};

// A pipeline szakaszai sorrendben (a folyamat-jelzőhöz is használható).
export const PIPELINE_STEPS: string[] = [
  "detect_lang_type", "mask_input", "load_context", "classify", "priority_triage",
  "retrieve", "policy_map", "escalation", "suggest_actions", "draft", "verify", "prepare_unmask",
];

export function stepLabel(step: string): string {
  return STEP_META[step]?.label ?? step;
}

export function fieldLabel(key: string): string {
  return FIELD_LABELS[key] ?? key;
}

const VALUE_MAPS: Record<string, Record<string, string>> = {
  generation_mode: { llm: "LLM-szintézis", insufficient: "nincs elég fedezet", template: "sablon" },
  format: { email: "e-mail levél", copilot: "beszédpont" },
  value: { surgos: "sürgős", normal: "normál" },
  tipus: { panasz: "panasz", nem_panasz: "nem panasz", hatokoron_kivuli: "hatókörön kívüli" },
};

/** Egy output-mező értékének közérthető magyar formázása. */
export function formatFieldValue(key: string, value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "igen" : "nem";
  if (Array.isArray(value)) return value.length ? value.map((v) => String(v)).join(", ") : "nincs";
  if (key === "confidence" && typeof value === "number") return `${Math.round(value * 100)}%`;
  const map = VALUE_MAPS[key];
  if (map && typeof value === "string" && map[value]) return map[value];
  return String(value);
}
