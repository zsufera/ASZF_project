# RAG-roadmap — ÁSZF-tudatos retrieval fejlesztési terv

> **Cél:** a retrieval pipeline okosítása **kifejezetten erre a use-case-re**: a forrásdokumentumok (ÁSZF + mellékletek + ESzSzF + Díjszabás) **egymásra hivatkoznak** (`cross_refs`) és **hierarchikus bekezdésekből** állnak (`paragrafus_szam`, pl. `5.5.1 ⊂ 5.5 ⊂ 5`). Ez a két strukturális tulajdonság ma nagyrészt **kihasználatlan**.
> **Forma:** stratégiai roadmap, tételenként a meglévő kódra illesztve. Minden tétel külön implementációs tervvé (`docs/superpowers/plans/`) bontható.
> **Kapcsolódó:** [`FEJLESZTESI_GUARDRAILS.md`](../FEJLESZTESI_GUARDRAILS.md) (termék-elvek), [`.claude/skills/rag-pipeline`](../.claude/skills/rag-pipeline/SKILL.md) (pipeline-leírás), [`docs/superpowers/specs/2026-06-08-agentic-answer-synthesis-design.md`](superpowers/specs/2026-06-08-agentic-answer-synthesis-design.md).

---

## 0. Jelenlegi állapot (kódra hivatkozva)

**Ingest:** `preprocessing/parse` → `data/processed/chunks.jsonl` (hierarchikus, § szintű, ~51k chunk). Chunk-mezők: `chunk_id`, `doc_id`, `source_file`, `szolgaltato`, `dok_tipus`, `dok_cim`, `oldalszam`, `paragrafus_szam`, `text`, `cross_refs`. Indexelés: `preprocessing/index.py::index_chunks` a **teljes chunk-dictet** tárolja Qdrant-payloadként.

**Két embedding-mód** (`preprocessing/embedding.py::active_mode`):
- `openai`: `text-embedding-3-large` → helyi Qdrant HNSW (`qdrant_semantic`), opcionális `szolgaltato`-szűrő.
- `deterministic` (kulcs nélkül / tesztek): `backend/retrieval.py` **hibrid lokális** út: `0.55·sparse + 0.45·dense`, ahol a „dense" a `deterministic_embedding` **64-dim hash** (`index.py`).

**Retrieval** (`backend/retrieval.py::retrieve`): top-5, majd `resolve_cross_refs` (+max 3). `rerank_chunks` = a hibrid pontszám (nem cross-encoder).

### Megerősített korlátok (ezek a roadmap kiindulópontjai)
| # | Korlát | Hely |
|---|---|---|
| L1 | **Cross-ref feloldás CSAK azonos dokumentumon belül** — a más dokra mutató hivatkozások (Díjszabás, ESzSzF) elvesznek | `retrieval.py::resolve_cross_refs` (`by_doc.get(doc_id)`) |
| L2 | A „dense" 64-dim **hash ≈ zaj** → fallback módban a keresés gyakorlatilag lexikai | `index.py::deterministic_embedding` |
| L3 | **Nincs valódi reranker** | `retrieval.py::rerank_chunks` |
| L4 | **Nincs query-rewrite**; a nyers, 400 karakterre vágott (maszkolt) üzenet a query | `agent/nodes.py::retrieve_node` |
| L5 | A cross-ref bővítés **statikus** (query-független, fix +3), **1-hop** | `retrieval.py::resolve_cross_refs` |
| L6 | **Nincs hatály/verzió-szűrés** — hatályon kívüli klauzula is bejöhet | retrieval egész |
| L7 | A hierarchia (`paragrafus_szam`) **nincs kihasználva** keresésnél/kontextusnál | retrieval egész |

---

## 1. Tervezési alapelvek

1. **Determinizmus előbb.** Ahol a struktúra (§-szám, hierarchia, explicit hivatkozás) determinisztikus választ ad, **ne** szemantikus keresésre bízzuk. Olcsóbb, pontosabb, auditálhatóbb.
2. **A meglévő metaadatra építünk** (`cross_refs`, `paragrafus_szam`, `mandatory_refs.yaml`, fájlnév-dátum) — sok tétel **új modell nélkül** megvalósítható.
3. **Jogi korrektség > recall.** Hiányos/hatályon kívüli forrásból inkább `insufficient` + eszkaláció, mint magabiztos hibás válasz (guardrails §2).
4. **Latencia-budget.** Minden új LLM-hívás ~15–20s (gpt-5-mini). Az index-idejű és determinisztikus megoldásokat preferáljuk a hot-path LLM-hívásokkal szemben; a hot-path bővítést env-flaggel kapcsolhatóvá tesszük.
5. **HITL/audit.** Minden behúzott forrás `retrieval_source`-szal jelölt legyen (`semantic` / `cross_ref` / `reference_closure` / `parent` …), hogy az ügyintéző és az audit lássa, miért van ott.

---

## 2. Roadmap tételenként

### A. Kereszthivatkozás mint valódi gráf

#### A1 — Cross-**doc** referencia-feloldás (determinisztikus)
- **Gap:** L1, L5. A más dokumentumra mutató hivatkozások („2. számú Díjszabás", „ESzSzF 1.1.2") nem oldódnak fel.
- **Javaslat:** indexkor építsünk **referencia-feloldó térképet**: (a) §-szám → `chunk_id` doc-on belül; (b) **melléklet/dok-név → `doc_id`** (pl. „2. számú Díjszabás" → a Díjszabás-melléklet `doc_id`-ja) a `dok_cim`/`source_file` mintákból. A `cross_refs` stringjeit normalizáljuk (`_normalize_ref` bővítése: dok-rész + §-rész). Retrievalkor a hivatkozott §-t **közvetlenül** húzzuk be (`retrieval_source: "cross_ref"`), dokumentumtól függetlenül.
- **Érintett kód:** `preprocessing/parse` (ref-string strukturálása), `retrieval.py::resolve_cross_refs` (cross-doc ág), új `reference_resolver` modul.
- **Adat/infra:** meglévő `cross_refs` + dok-név mapping (kis YAML/heurisztika). **Nincs új modell.**
- **Erőfeszítés:** M · **Kockázat:** alacsony · **Re-index:** nem feltétlen (a mapping lehet runtime).

#### A2 — Referencia-LEZÁRÁS (reference closure) generálás előtt  ⭐ legnagyobb domain-érték
- **Gap:** a válasz olyan §-ra támaszkodhat, aminek **kivétele/feltétele** egy be-nem-húzott §-ban van (pl. „rendes felmondás 60 nap", de a hűségidős kivétel máshol).
- **Javaslat:** a kiválasztott §-ok **tranzitív hivatkozási lezárását** számoljuk ki (A1 felett, bounded mélység), és a `policy_map`/`draft` csak a **lezárt** forráshalmazra alapozzon. A nem feloldható hivatkozás → completeness-hiány jel (lásd A4).
- **Érintett kód:** új `reference_closure` lépés a `retrieve` és a `policy_map_node` közé; a `synthesize_answer` a lezárt forrásokat kapja.
- **Adat/infra:** A1. **Nincs új modell.**
- **Erőfeszítés:** M · **Kockázat:** alacsony-közepes (forrás-robbanás ellen mélység-/darab-korlát) · **Re-index:** nem.

#### A3 — Több-hop, query-pontozott gráf-bejárás (GraphRAG-szerű)
- **Gap:** L5 (statikus, 1-hop). 
- **Javaslat:** a korpusz mint irányított gráf (élek: `cross_refs` + szülő/gyerek hierarchia). Top-k szemantikus mag után 2–3 hop bővítés, minden bővített csomópont **pontozva**: `saját_relevancia × hop_decay × él_típus_súly`. A `resolve_cross_refs` általánosítása.
- **Érintett kód:** `retrieval.py` (gráf-építés + pontozott bejárás), előfeltétel A1.
- **Erőfeszítés:** M-L · **Kockázat:** közepes (zaj-bevonás → kell a pontozás+küszöb) · **Re-index:** nem.

#### A4 — Hiányzó hivatkozás = completeness-jel → CRAG-loop / eszkaláció
- **Javaslat:** ha egy top-§ hivatkozik X-re és X nem feloldható/nem behúzható → vagy újra-retrieval (E1), vagy `missing_reference` jel → eszkaláció. Rákapcsolódik a most javított `policy_map.missing_mandatory` + `escalation` logikára.
- **Érintett kód:** `retrieval.py` / `policy_map.py` (jel előállítás), `agent/nodes.py::escalation_node` (új trigger).
- **Erőfeszítés:** S (A1 után) · **Kockázat:** alacsony.

### B. Bekezdés-hierarchia kihasználása

#### B1 — Small-to-big (parent retriever)
- **Gap:** L7. A leaf § pontos, de töredékes kontextus → az LLM félreértheti.
- **Javaslat:** keress a **leaf** szinten, de a generáláshoz a **szülő szakaszt** add (`5.5.1` → `5.5` teljes szövege). A szülő a `paragrafus_szam` prefixéből determinisztikus. Ha a szülő nem külön chunk, rekonstruáld a testvér-leafek összefűzéséből.
- **Érintett kód:** `retrieval.py` (parent-lookup a `chunk_to_result` után), esetleg `preprocessing/parse` (parent-chunk megőrzése).
- **Erőfeszítés:** M · **Kockázat:** alacsony · **Re-index:** opcionális (ha parent-chunkot is tárolunk).

#### B2 — Auto-merging retrieval
- **Javaslat:** ha több **testvér-leaf** talál ugyanazon szülő alatt (`5.5.1`+`5.5.2`+`5.5.3`), add vissza a **szülőt** egyben. Kevesebb fragmentáció.
- **Érintett kód:** `retrieval.py` (merge-lépés a rerank után).
- **Erőfeszítés:** M · **Kockázat:** alacsony · **Re-index:** B1-gyel közös.

#### B3 — Kategória → szekció routing  ⭐ olcsó precízió
- **Javaslat:** a `classify` kategóriát a `mandatory_refs.yaml` **paragrafus-aihoz** kötve **biasold/elő-szűrd** a retrievalt a hierarchia helyes ágára (számlázás → `5.x` + Díjszabás; felmondás → `7.x`). Pl. boost a kategória-prefixű `paragrafus_szam`-okra.
- **Érintett kód:** `agent/nodes.py::retrieve_node` (kategória átadása), `retrieval.py` (paragrafus-prefix boost/filter), forrás: `policy_map.load_mandatory_entries`.
- **Erőfeszítés:** S · **Kockázat:** alacsony · **Re-index:** nem.

#### B4 — Hierarchikus breadcrumb az embeddingbe és a UI-ba
- **Javaslat:** indexkor a leaf elé fűzd az útvonalat („ÁSZF törzs › 5. Számlázás › 5.5 Számlakifogás › 5.5.1 …") → az embedding tudja, hol ül; a UI forrás-kártyán megjelenik (`RichSourceCard`).
- **Érintett kód:** `preprocessing/parse`/`index.py` (breadcrumb-mező + embed-szöveg), `frontend` `SourceRef`/`RichSourceCard`.
- **Erőfeszítés:** S · **Kockázat:** alacsony · **Re-index:** **igen** (új embed-szöveg).

### C. Jogi-szöveg-specifikus minőség

#### C1 — Cross-encoder reranker
- **Gap:** L3. A jogi szöveg lexikailag homogén → near-duplikátumok.
- **Javaslat:** a top-k (pl. 20) fölött cross-encoder rerank → top-5. Lokális reranker-modell vagy API. A `rerank_chunks` valódi rerankerre cserélése (a hibrid pontszám marad pre-filternek).
- **Érintett kód:** `retrieval.py::rerank_chunks` + új `reranker` adapter.
- **Adat/infra:** reranker-modell (lokális vagy API). **Új függőség.**
- **Erőfeszítés:** M · **Kockázat:** közepes (latencia/függőség) · **Re-index:** nem.

#### C2 — Numerikus / §-szám-tudatos hibrid
- **Gap:** az embeddingek gyengék számokra (határidők, díjak, %, §-számok).
- **Javaslat:** dedikált **exact numeric/§-szám jel** a hibrid pontszámba (a `sparse_score` mellé), boost ha a query száma/§-e a chunkban van.
- **Érintett kód:** `retrieval.py::hybrid_score` (numerikus komponens).
- **Erőfeszítés:** M · **Kockázat:** alacsony · **Re-index:** nem.

#### C3 — Hatály/verzió-szűrő  ⭐ jogi korrektség
- **Gap:** L6. A fájlnévben ott a dátum (`…hatalyos_20260605`), de nincs szűrés.
- **Javaslat:** parse-old a hatály-dátumot metaadatba; a retrieval **a hatályos verziót preferálja**, és kérdéskor (vagy adott referencia-dátumra) **soha ne keverjen hatályon kívüli** klauzulát.
- **Érintett kód:** `preprocessing/parse` (dátum-mező), `retrieval.py` (verzió-preferencia/filter).
- **Erőfeszítés:** S-M · **Kockázat:** alacsony · **Re-index:** **igen** (ha új metaadat-mező).

### D. Reprezentáció / index

#### D1 — Lokális embedding fallback (a hash-zaj helyett)
- **Gap:** L2. Kulcs nélkül a keresés gyakorlatilag lexikai.
- **Javaslat:** vagy egy **kis lokális (magyar/multilingual) embedding-modell** valódi szemantikus fallbacknek, vagy **őszintén** sparse + strukturális jelek (és a 64-dim hash eltávolítása, hogy ne keltsen ál-szemantikát).
- **Érintett kód:** `preprocessing/embedding.py`, `index.py::deterministic_embedding`, `retrieval.py::dense_score`.
- **Adat/infra:** lokális modell (pl. ONNX/sentence-transformers). **Új függőség.**
- **Erőfeszítés:** M-L · **Kockázat:** közepes · **Re-index:** **igen**.

#### D2 — Multi-vector / HyDE index-időben
- **Gap:** a jogi szöveg állító, a query kérdő.
- **Javaslat:** indexkor minden §-hoz generált **hipotetikus kérdések** („milyen kérdést válaszol meg ez a szakasz") külön vektorként; a query azokra is keres.
- **Érintett kód:** `preprocessing/index.py` (LLM-es index-idejű generálás), `retrieval.py` (multi-vector keresés).
- **Adat/infra:** LLM-hívás ~51k chunkra (drága — részhalmaz/cache javasolt). **Re-index:** **igen**.
- **Erőfeszítés:** L · **Kockázat:** közepes (index-költség).

### E. Agentic retrieval-hurok (összekötő)

#### E1 — Iteratív / Corrective-RAG a gráffal
- **Javaslat:** `keres → relevancia + teljesség-grade → ha hiányos VAGY be-nem-húzott hivatkozás → determinisztikus ref-feloldás (A1) + query-rewrite (L4) → újra`. Bounded (max 2 kör). A most már LLM-judge `verify` (`backend/verify.py`) vezérelheti: nem megalapozott → célzott újra-retrieval.
- **Érintett kód:** `agent/graph.py` (feltételes él + retry-számláló — a lineáris pipeline első valódi hurka), `agent/nodes.py` (grade + re-retrieve node-ok).
- **Erőfeszítés:** M-L · **Kockázat:** közepes (determinizmus megőrzése → szigorú bounding) · **Re-index:** nem.

---

## 3. Prioritált ütemterv

### Fázis 1 — Gyors nyeremények (determinisztikus, meglévő metaadat, nincs új modell)
**A1** cross-doc ref-feloldás · **A2** reference-closure · **A4** completeness-jel · **B3** kategória→szekció routing · **C3** hatály-szűrő · **B1** small-to-big.
> Ez a fázis adja a legnagyobb jogi-domain értéket a legkisebb kockázattal. A1+A2 a kulcs.

### Fázis 2 — Közepes (némi infra / index-bővítés)
**A3** gráf-bejárás · **B2** auto-merging · **B4** breadcrumb (re-index) · **C1** reranker · **C2** numerikus hibrid.

### Fázis 3 — Architekturális / nagyobb
**D1** lokális embedding fallback (re-index) · **D2** multi-vector/HyDE (re-index) · **E1** agentic retrieval-loop.

### Függőségek
- A2 → A1; A3 → A1; A4 → A1; E1 → A1 + L4(query-rewrite).
- B2 → B1.
- **Re-indexet igénylők** (egyszerre érdemes): B4, C3, D1, D2 (+ esetleg C2, ha index-mező).

---

## 4. Mérés (a fejlődés bizonyítása)

A meglévő `eval/` harness (`config/eval_targets.yaml`) bővítése — **retrieval- és citation-metrikák**, hogy a roadmap tételei mérhetők legyenek:
- **Retrieval@k / recall@k** mandatory-§-re: a kötelező hivatkozás benne van-e a top-k-ban (a `mandatory_refs.yaml` ground-truthként).
- **Citation-completeness** (A2 metrikája): a behúzott források hivatkozási lezárása teljes-e (nincs be-nem-húzott, de hivatkozott §).
- **Mandatory-coverage rate** és **escalation rate**: a B3/A1 hatása (jó retrievalnál a `missing_mandatory` ritkábban sül el).
- **Faithfulness / context precision** (RAGAS-szerű): az LLM-judge `verify_mode="llm"` kimenetéből aggregálva.
- **Hatály-tisztaság** (C3): hatályon kívüli klauzula aránya a forrásokban (0 a cél).
- **Latencia p95** per fázis (a hot-path bővítések költsége).

---

## 5. Nem-célok / mit NE építsünk
- **Nyílt végű, autonóm retrieval-ágens** korlátlan hurkokkal — a bounding és a determinizmus elsődleges (guardrails §6, §2).
- **Nehéz multi-ágens orchestráció** — a lineáris gerinc + célzott hurok (E1) jobb illeszkedés.
- **Teljes korpusz LLM-es újrafeldolgozása** költségvetés nélkül (D2-nél részhalmaz/cache).
- A szolgáltatók dokumentumainak keveredése a retrievalben (guardrails §5) — minden bővítésnél tartandó a `szolgaltato`-szűrés.

---

## 6. Javasolt első lépés
**Fázis 1 / A1 + A2** (cross-doc referencia-feloldás + reference-closure) önálló spec + implementációs terv: tisztán determinisztikus, a meglévő `cross_refs`-re épül, közvetlenül csökkenti a „hiányos/megalapozatlan válasz" kockázatot, és előfeltétele az A3/A4/E1-nek. Mérőszám: citation-completeness + mandatory recall@k.
