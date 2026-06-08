# Cross-doc referencia-feloldás + reference-closure (RAG A1+A2) — Design

> **Dátum:** 2026-06-08
> **Cél:** Az ÁSZF-korpusz **kereszthivatkozásait** kihasználni a retrievalben: a visszakeresett §-ok által hivatkozott (lokális ÉS más dokumentumban lévő) szakaszokat **determinisztikusan behúzni** (reference-closure), hogy a válasz ne támaszkodjon olyan szabályra, aminek kivétele/feltétele egy be-nem-húzott §-ban van. A feloldhatatlan hivatkozás **completeness-jelként** jelenik meg.
> **Roadmap-tétel:** [`docs/rag-roadmap.md`](../../rag-roadmap.md) A1 + A2 (+ A4 horog).
> **Backend HTTP-szerződés:** nem változik (a `/retrieve` válasz bővül `unresolved_refs`-szel; a `chunks[]` elemei `reference_closure` `retrieval_source`-szal jelölve).

---

## 0. Adat-valóság (a tervet megalapozó vizsgálat)

- A meglévő `cross_refs` mező **használhatatlan alapnak**: 51 049 chunkból csak **142**-nél van, és zajos lokális stringek (`['VI. pont']`, `['5.6 pont']`, `['li. \nPont']`). **Dokumentum-hivatkozás nincs benne.**
- A valódi hivatkozások a chunk **szövegében** vannak: **1559+** chunk tartalmaz kereszt-dok kifejezést (`„3. számú melléklete szerint"`, `„2/B. számú melléklet"`, `„Díjszabás"`, `„ESzSzF"`), plusz sok lokális `§/pont`.
- A jelenlegi `CROSS_REF_PATTERN` (`preprocessing/parse.py:25`) csak lokális `\d+(\.\d+){1,4}\s*pont|bekezdés`, `\d+\s*§`, `[IVXLCDM]+\.\s*fejezet|pont`-ot fog — **kereszt-dok mintát nem**.
- A dok-név → `doc_id` leképezés levezethető a `source_file`-ból (32 dokumentum, pl. `ASZF_2A_mobil_melleklet_hatalyos_20260605` ↔ „2/A. számú melléklet", `ASZF_3_melleklet_hatalyos_20260605` ↔ „3. számú melléklet").

## 1. Döntések (jóváhagyott)

| # | Döntés | Választott |
|---|---|---|
| 1 | Hivatkozás-kinyerés helye | **Ingest-időben** (parse) + a meglévő `chunks.jsonl` backfillje, majd Qdrant re-index |
| 2 | Closure mértéke | **1 hop, max +5** behúzott forrás |
| 3 | `cross_refs` séma | `list[str]` → **`list[dict]`** strukturált (`raw`, `doc_hint`, `paragraph`) |
| 4 | Feloldhatatlan / kétértelmű hivatkozás | **Konzervatív**: nem húzunk be rosszat → `unresolved`-be kerül (completeness-jel) |

## 2. Architektúra

```
preprocessing/parse.py
  extract_references(text) -> list[dict]          # lokális + kereszt-dok, strukturáltan
        │ (a Chunk.cross_refs új sémája)
        ▼
data/processed/chunks.jsonl  (parse VAGY backfill termeli)
        │
        ▼
backend/reference_resolution.py  (ÚJ, tiszta/tesztelhető)
  build_doc_name_index(chunks)   -> {normalizált dok-név: doc_id}
  build_paragraph_index(chunks)  -> {(doc_id, norm_paragraph): chunk}
  resolve_reference(ref, source_doc_id, indexes) -> chunk | None
  reference_closure(seed_chunks, all_chunks, max_hops=1, max_extra=5) -> (added, unresolved)
        │
        ▼
backend/retrieval.py :: retrieve()
  a resolve_cross_refs HELYETT reference_closure → chunks += added (retrieval_source="reference_closure")
  return {..., "unresolved_refs": [...]}           # A4 completeness-jel
```

### Egységek és felelősségek
- **`extract_references(text)`** (`preprocessing/parse.py`): tiszta függvény, szöveg → strukturált hivatkozások. Az `extract_cross_refs`-et váltja.
- **`backend/reference_resolution.py`** (ÚJ): a feloldás és a closure tiszta logikája, I/O nélkül (a chunk-listát paraméterként kapja). Külön tesztelhető.
- **`retrieve()`** (`backend/retrieval.py`): csak orchestrál — a `resolve_cross_refs` helyett a `reference_closure`-t hívja.

## 3. Adat-szerződés

### `cross_refs` elem (strukturált)
```jsonc
{ "raw": "2/B. számú melléklet 4.1.4 pont", "doc_hint": "2/B. számú melléklet", "paragraph": "4.1.4" }
// lokális hivatkozás:
{ "raw": "5.6 pont", "doc_hint": null, "paragraph": "5.6" }
```
- `doc_hint`: `None`, ha a hivatkozás a saját dokumentumra mutat; egyébként a normalizálható dok-megjelölés.
- `paragraph`: a hivatkozott §/pont szám (`None`, ha csak dok-szintű, pl. csak „Díjszabás").

### `retrieve()` válasz (bővítve)
```jsonc
{
  "chunks": [ ... ,  { ...chunk..., "retrieval_source": "reference_closure" } ],
  "retrieval_mode": "...",
  "result_count": N,
  "unresolved_refs": [ { "raw": "...", "doc_hint": "...", "paragraph": "..." } ]   // ÚJ
}
```

## 4. Komponensek — részletek

### 4.1 `extract_references(text) -> list[dict]` (`preprocessing/parse.py`)
Minták (case-insensitive), prioritás szerint:
- **Kereszt-dok:** `(?P<doc>\d+[A-Z]?(?:/[A-Z])?\.?\s*számú\s*(?:melléklet|függelék))(?:\s*(?P<para>\d+(?:\.\d+){0,4}))?` → `doc_hint`=doc, `paragraph`=para (ha van).
- **Nevesített dok:** `Díjszab\w*`, `ESzSzF`, `Függelék` önállóan → `doc_hint`=match, `paragraph`=None.
- **Lokális §:** `\d+(?:\.\d+){1,4}\s*(?:pont|bekezdés)?`, `\d+\s*§`, `[IVXLCDM]+\.\s*(?:fejezet|pont)` → `doc_hint`=None, `paragraph`=normalizált szám.
- Deduplikálás `(doc_hint, paragraph)` szerint; üres/garbage (`li.`, túl rövid) kiszűrve.

### 4.2 `build_doc_name_index(chunks)` (`backend/reference_resolution.py`)
A `source_file`/`dok_cim`-ből normalizált kulcsok → `doc_id`. Normalizálás: kisbetű, ékezet-fold, `melleklet`/`fuggelek` tövek, a melléklet-szám több alakja (`2/a`, `2a`, `2`). Pl. `ASZF_2A_mobil_melleklet_…` → `{"2/a melleklet","2a melleklet"}` → `doc_id`. **Kétértelmű kulcs** (több doc_id) → a kulcsot eldobjuk (konzervatív).

### 4.3 `resolve_reference(ref, source_doc_id, doc_name_index, paragraph_index) -> chunk | None`
1. Cél `doc_id`: ha `ref.doc_hint` → `doc_name_index` lookup (normalizálva); ha nincs/kétértelmű → `None` (unresolved). Ha `doc_hint is None` → `source_doc_id`.
2. Ha van `paragraph`: `paragraph_index[(doc_id, norm_paragraph)]` (prefix-egyezés is: `5.5` ~ `5.5.1`). Ha nincs `paragraph` (csak dok-szint) → a cél dok **első/legrelevánsabb** chunkja **nem** húzódik be automatikusan (túl tág) → `None`/unresolved.
3. Találat → a chunk; egyébként `None`.

### 4.4 `reference_closure(seed_chunks, all_chunks, max_hops=1, max_extra=5) -> (added, unresolved)`
- Indexek egyszeri felépítése `all_chunks`-ból.
- A `seed_chunks` (top-k retrieval) `cross_refs`-ein végigmegy; minden ref-et felold.
- Feloldott és még nem látott chunk → `added` (`retrieval_source="reference_closure"`, `score` a forrás score-ja − 0.05, min 0.01). **Max +5** összesen; `max_hops=1` (a behúzott chunkok hivatkozásait NEM követjük tovább).
- Feloldhatatlan ref → `unresolved`.

### 4.5 Retrieval-integráció
A `retrieve()` a `resolve_cross_refs(primary, all_chunks)` helyett: `added, unresolved = reference_closure(primary, all_chunks)`, majd `chunks = primary + added`, és a válaszban `unresolved_refs=unresolved`. A `resolve_cross_refs` törölhető (vagy vékony wrapper a kompatibilitásért, ha más hivatkozza — ellenőrizni).

### 4.6 Adat-regenerálás
- `extract_references` bekerül a `parse`-ba (jövőbeli ingest helyes).
- **Backfill** (`preprocessing/enrich_cross_refs.py`, ÚJ CLI): beolvassa a `chunks.jsonl`-t, minden chunk `cross_refs`-ét újraszámolja a `text`-ből az `extract_references`-szel, visszaírja. **Nincs PDF re-parse.**
- **Qdrant re-index** (`python -m preprocessing.index`): a szöveg változatlan → embedding-cache találat → olcsó; a payload `cross_refs` konzisztens lesz. *A closure a lokális `chunks.jsonl`-ből dolgozik, így a feature a backfill után re-index nélkül is működik.*

## 5. Hibakezelés
- Feloldhatatlan/kétértelmű hivatkozás → `unresolved` (nem kivétel, nem hiba).
- `max_extra`/`max_hops` korlát a forrás-robbanás ellen.
- A `reference_closure` és az extrakció kivételbiztos (üres/rossz szöveg → üres lista), a retrieval sosem száll el a closure miatt.
- A `szolgaltato`-szűrés tiszteletben tartva: a closure ne húzzon be más szolgáltató dokumentumából (a `resolve_reference` ellenőrzi a forrás `szolgaltato`-ját).

## 6. Tesztelés (hermetikus, re-index nélkül)
**Unit:**
- `extract_references`: lokális (`„5.6 pont"`, `„7 §"`), kereszt-dok (`„2/B. számú melléklet 4.1.4 pont"`, `„3. számú melléklet"`, `„Díjszabás"`), garbage kiszűrése, dedup.
- `build_doc_name_index`: valós `source_file`-nevekkel (`ASZF_2A_mobil_melleklet…`) helyes kulcsok; kétértelmű kulcs eldobva.
- `resolve_reference`: lokális §, kereszt-dok §, feloldhatatlan → None; más szolgáltató nem oldódik fel.
- `reference_closure`: 1-hop, `max_extra=5` betartva, `unresolved` gyűjtve, nincs duplikátum a seeddel.

**Integráció:**
- `retrieve()` egy olyan korpusz-fixture-rel, ahol A chunk hivatkozik B-re → B bekerül `retrieval_source="reference_closure"`-szal; feloldhatatlan ref → `unresolved_refs`.

**Backfill smoke (opcionális, manuális):** a `enrich_cross_refs` egy kis fixture `chunks.jsonl`-en strukturált `cross_refs`-et termel.

## 7. Hatókörön kívül (YAGNI / külön roadmap-tétel)
- Több-hop gráf-bejárás (A3), reranker (C1), query-rewrite/CRAG-loop (E1), hierarchia (B*), hatály-szűrő (C3) — külön tételek.
- Az `unresolved_refs` → eszkaláció bekötése (A4 teljes) — most csak **expozíció**; az `escalation_node` bekötése későbbi kis lépés.
- A dok-szintű (paragraph nélküli) hivatkozás automatikus chunk-behúzása (túl tág; szándékosan `unresolved`).
