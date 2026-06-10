# Bug-audit és javítási terv (2026-06-09)

> Kód-audit eredménye az agentic flow, LLM-hívások, RAG/retrieval és indexelés területein.
> Minden javításhoz **reprodukáló regressziós teszt** készül előbb (TDD, hermetikus — ld. `tests/conftest.py` és `.claude/skills/add-llm-call`).

## Súlyossági összefoglaló

| # | Hiba | Terület | Súlyosság |
|---|------|---------|-----------|
| 1 | Udvarias panasz „nem_panasz"-nak minősül | agent flow | **súlyos** |
| 2 | `/reindex` local Qdrant mellett nem működik futó backenden | indexelés | **súlyos** |
| 3 | LLM-konfidencia validálatlan (eszkalációs küszöb kijátszható) | LLM-hívás | **súlyos** |
| 4 | `search_qdrant` némán nyel el minden kivételt | RAG | **súlyos** |
| 5 | `rewrite_mode` hamisan „llm"-et jelent | LLM-hívás | közepes |
| 6 | `escalation_mode` nem a ténylegesen futott utat jelzi | LLM-hívás | közepes |
| 7 | Üres LLM-citations → összes forrás „hivatkozottnak" jelölve | LLM-hívás | közepes |
| 8 | Classify-kandidátusok normalizálása inkonzisztens | LLM-hívás | közepes |
| 9 | Audit-persist hiba némán elnyelve + hibás `started_at` | agent flow | közepes |
| 10 | Paragrafus-egyezés normalizálás nélkül (`missing_mandatory`) | RAG | közepes |
| 11 | Hiányzó `Path` import a `backend/retrieval.py`-ban | RAG | kicsi |
| 12 | `id()`-alapú cache-kulcs a reference resolutionben | RAG | kicsi |
| 13 | `set` kerül a cache-elt chunk dictekbe | indexelés | kicsi |
| 14 | `auto_merge_siblings` a limit-vágás után fut, pótlás nélkül | RAG | kicsi |
| 15 | `embed_documents` csendes `None`-szűrése | indexelés | kicsi |

---

## 1. Udvarias panaszlevél „nem_panasz"-nak minősül — SÚLYOS

**Hely:** `agent/nodes.py:29` (`NEM_PANASZ_HINTS`) + `detect_lang_type` (`agent/nodes.py:95`), kategória-felülírás: `classify_node` (`agent/nodes.py:163`).

**Tünet:** A `NEM_PANASZ_HINTS = ("köszön", "köszönet", "rendben volt", …)` substring-egyezéssel **bárhol** a szövegben talál. Egy valódi panasz, ami úgy zárul, hogy *„Köszönöm a mielőbbi intézkedést"* vagy *„Köszönettel, Kovács Anna"*, illetve tartalmazza, hogy *„korábban minden rendben volt"*, `tipus = "nem_panasz"` lesz → a kategória `egyeb`-re íródik felül, a javasolt akció `koszonet_valasz`, és az eszkalációs ág kikerül. A minta-emailek `Üdvözlettel`-lel záródnak, ezért a demó és a meglévő teszt nem bukik el rajta.

**Javítás:**
- Az aláírás-blokk (utolsó 1–2 sor, `Köszönettel,` / `Üdvözlettel,` típusú záróformulák) kizárása a hint-elemzésből, ÉS
- a `nem_panasz` minősítés csak akkor győzzön, ha **panasz-jel nincs** a szövegben (a `CATEGORY_KEYWORDS` bármely kulcsszava vagy a `TRIGGER_KEYWORDS` találata felülírja a köszönet-hintet).

**Regressziós teszt:** panasz-szöveg `„…a számlám hibás. Köszönöm a mielőbbi intézkedést. Köszönettel, [NÉV_1]"` → `lang_type.tipus == "panasz"`, a kategória nem íródik felül. Meglévő `test_agent_run_detects_nem_panasz` változatlanul zöld marad.

---

## 2. `/reindex` beágyazott (local) Qdrant mellett nem működik futó backenden — SÚLYOS

**Hely:** `backend/reindex_service.py:29` (`index_chunks(chunks=chunks)`), `preprocessing/index.py:134` (`make_client`) és `:149` (`get_shared_client`).

**Tünet:** Default config (`QDRANT_MODE=local`) mellett a retrieval a `get_shared_client()` singletonnal nyitva tartja a `data/qdrant_local` mappát. Az `index_chunks` saját `make_client()`-et nyit ugyanarra a path-ra — az embedded Qdrant ezt nem engedi („already accessed by another instance"). Az első retrieval után minden `POST /reindex` Qdrant-indexelése elhasal; a hiba csak a `qdrant_status: "failed: …"` mezőben látszik, a végpont 200-at ad. Siker esetén sem frissülne a singleton, így a retrieval a régi indexet látná. Mellékhiba: a `force` paramétert a `run_reindex` nem adja tovább az `index_chunks`-nak → a `force=true` (embedding-cache bypass) no-op.

**Javítás:**
- `run_reindex` a **megosztott klienst** használja: `index_chunks(chunks=chunks, force=force, client=get_shared_client())` — egyetlen kliens, nincs ütközés, és a frissen írt collectiont ugyanaz a példány szolgálja ki.
- Alternatíva (server mód felé): local módban a reindex előtt a singleton lezárása + reset (`close_shared_client()` új helper), majd reindex után friss kliens. Az első megoldás az egyszerűbb és elégséges.
- `force` paraméter átvezetése.
- `qdrant_status: failed` esetén `logger.exception` + a HTTP-válaszban explicit jelzés (a UI is mutassa).

**Regressziós teszt:** `run_reindex` hívás mockolt `index_chunks`-szal — assert: megkapja a `force` és `client` argumentumot; külön teszt arra, hogy `qdrant_status` failed esetén log keletkezik.

---

## 3. LLM-konfidencia validálatlan — eszkalációs küszöb kijátszható — SÚLYOS

**Hely:** `backend/classify.py:98` (`confidence = float(data.get("konfidencia", 0.6))`).

**Tünet:** Nincs [0,1] tartomány-ellenőrzés. Ha a modell százalékot ad vissza (pl. `85`), az `alacsony_konfidencia` eszkalációs ok (küszöb: 0.75) soha nem aktiválódik, a frontend „8500%"-ot mutat. Sérül a repo-idióma: „validáld az LLM kimenetét, érvénytelennél ess vissza".

**Javítás:** clamp + heurisztika a `classify_message` LLM-ágában:
- ha `1 < konfidencia <= 100` → osztás 100-zal (százalékos formátum normalizálása);
- ha ezután sincs [0,1]-ben, vagy nem szám → `ValueError` → meglévő rule-fallback.
- Ugyanez a `tobb_jelolt[*].konfidencia` értékekre.

**Regressziós teszt:** mockolt `chat_json` `{"konfidencia": 85, ...}` → `confidence == 0.85`; `{"konfidencia": "magas"}` → `classify_mode == "rule"` (fallback).

---

## 4. `search_qdrant` némán nyel el minden kivételt — SÚLYOS

**Hely:** `backend/retrieval.py:169-170` (`except Exception: return []`).

**Tünet:** Konfighiba (rossz `OPENAI_EMBED_DIM`, korrupt collection, hiányzó index) megkülönböztethetetlen a „nincs találat"-tól: a rendszer csendben a lexikai `hybrid_local` útra esik (jelentős minőségromlás), log nélkül. Pontosan az a hibaosztály, amire a CLAUDE.md figyelmeztet (néma fallback).

**Javítás:** `logger.exception("search_qdrant failed; falling back to hybrid_local")` az except-ágban (a fallback-viselkedés marad — ez a kívánt degradáció, csak láthatóvá kell tenni). Megfontolandó: a `retrieve` válaszába `retrieval_warning` mező, hogy az audit/UI is jelezze a degradált módot.

**Regressziós teszt:** mockolt `get_shared_client`, ami kivételt dob → a `retrieve` `hybrid_local` módban fut le ÉS a caplog tartalmazza az exception-logot.

---

## 5. `rewrite_mode` hamisan „llm"-et jelent — közepes

**Hely:** `backend/llm_tasks.py:37` (`"llm" if query != text else "rule"`).

**Tünet:** A determinisztikus fallback (`backend/query_rewrite.py:39`) kategória-kulcsszavakat fűz a szöveg elé, tehát rule-úton is `query != text` → a Copilot-út (`rag_service`) `rewrite_mode="llm"`-et jelent LLM-hívás nélkül.

**Javítás:** a `rewrite_query` adja vissza maga a módot — szignatúra-bővítés: `rewrite_query(...) -> tuple[str, str]` vagy `{"query": ..., "mode": ...}` dict; az `llm_tasks.rewrite_query_task` ezt vezesse át. (A `agent/nodes.py::retrieve_node` hívóhelyét is igazítani kell.)

**Regressziós teszt:** LLM nélkül (`openai_api_key=""`) → `rewrite_mode == "rule"` akkor is, ha a query bővült; mockolt `chat_json`-nal → `"llm"`.

---

## 6. `escalation_mode` nem a ténylegesen futott utat jelzi — közepes

**Hely:** `agent/nodes.py:253` (`result["escalation_mode"] = "rule+llm" if llm_available() else "rule"`).

**Tünet:** Ha az `llm_escalation_suggestion` belül kivétellel elszállt (fallback `{suggested: False, okok: []}`), a mód akkor is „rule+llm". Az audit nem tükrözi, melyik út futott.

**Javítás:** az `llm_escalation_suggestion` adjon vissza explicit `"llm_ok": bool` mezőt (siker = True, nem-elérhető/hiba = False); az `escalation_node` ebből származtassa: `"rule+llm" if suggestion["llm_ok"] else "rule"`. A `llm_tasks.suggest_escalation_task` mode-logikáját ugyanerre az alapra kell hozni (ott most a `suggested` flagből származik, ami az LLM „nem javaslom" válaszát is „rule"-nak címkézi).

**Regressziós teszt:** mockolt `chat_json` kivételt dob → `escalation_mode == "rule"`; mockolt sikeres válasz (`eszkalacio: false`) → `"rule+llm"`.

---

## 7. Üres LLM-citations → összes forrás „hivatkozottnak" jelölve — közepes

**Hely:** `backend/draft.py:282` (`"citations": cited or [s["chunk_id"] for s in sources]`).

**Tünet:** Ha az LLM egyetlen forrást sem használt ([Sn] jelölő és `felhasznalt_forrasok` is üres), a draft az ÖSSZES forrást hivatkozottként jelenti → a verify mindet ellenőrzi (jellemzően ungrounded-warning), és az audit hamis hivatkozás-listát rögzít.

**Javítás:** üres `cited` esetén **ne** töltsük fel az összes forrással — ez gyakorlatilag fedezet nélküli válasz: vagy `_insufficient_result`-ra esünk (konzervatív, ajánlott), vagy üres `citations`-szel térünk vissza és a verify/`prepare_unmask` természetes módon blokkolja az approve-t.

**Regressziós teszt:** mockolt `chat_json` válasz jelölők nélkül → `generation_mode == "insufficient"` (vagy `citations == []`), és `ready_for_approval is False` a pipeline végén.

---

## 8. Classify-kandidátusok normalizálása inkonzisztens — közepes

**Hely:** `backend/classify.py:95` (fő kategória: `fold_text(...).strip().replace(" ", "_")`) vs `:101` (kandidátus: csak `fold_text(...)`).

**Tünet:** A szóközös formában visszaadott jelöltek (pl. „hibabejelentés szolgáltatáskiesés") némán kiesnek a `tobb_jelolt` listából, miközben fő kategóriaként átmennének.

**Javítás:** közös `_normalize_category(raw: str) -> str` helper, mindkét helyen ugyanazzal a normalizálással.

**Regressziós teszt:** mockolt `chat_json` szóközös kandidátussal → a kandidátus szerepel a `candidates`-ben aláhúzásos formában.

---

## 9. Audit-persist hiba némán elnyelve + hibás `started_at` — közepes

**Hely:** `agent/runner.py:116-119` (`except sqlite3.Error: pass`), `runner.py:48` (`started_at` a futás VÉGÉN áll be, mert a `persist_agent_run` a `graph.invoke` után hívódik).

**Tünet:** Auditálhatóságra épülő rendszerben az audit-rekord csendben elveszhet; a DB-ből a futásidő nem rekonstruálható (started ≈ ended).

**Javítás:** `logger.exception("persist_agent_run failed for case %s", case_id)` a `pass` helyett (a futás eredményét továbbra sem dobjuk el emiatt). A valós kezdő-időpont a `run_agent`-ben mérendő és paraméterként adandó át a `persist_agent_run`-nak.

**Regressziós teszt:** mockolt `sqlite3.connect` ami `sqlite3.Error`-t dob → a `run_agent` eredményt ad vissza ÉS caplog-ban ott a hiba; persist-teszt: `started_at < ended_at` és a delta ≈ a mért futásidő.

---

## 10. Paragrafus-egyezés normalizálás nélkül (`missing_mandatory`) — közepes

**Hely:** `backend/policy_map.py:83-92` (pontos string-egyezés), ugyanez a minta: `backend/retrieval.py:187` (`apply_category_boost`).

**Tünet:** `"5.2."` ≠ `"5.2"` formátum-eltérésnél hamis „hiányzó kötelező hivatkozás" → felesleges eszkaláció; a kategória-boost is kihagyhat találatot. A `normalize_paragraph` (`backend/reference_resolution.py:22`) létezik, csak itt nincs használva.

**Javítás:** mind a `present_paragrafus` halmaz, mind az entry-oldali `paragrafus` `normalize_paragraph`-on át menjen; az `apply_category_boost` / `category_mandatory_paragraphs` ugyanígy.

**Regressziós teszt:** chunk `paragrafus_szam="5.2."`, mandatory entry `paragrafus="5.2"` → `missing_mandatory == []`.

---

## 11. Hiányzó `Path` import — kicsi

**Hely:** `backend/retrieval.py:45` (`_chunk_cache_path: Path | None`).

**Tünet:** Csak a `from __future__ import annotations` miatt nem dob `NameError`-t; `typing.get_type_hints` és IDE-típusellenőrzés törik rajta. A `retrieve(chunks_path: Any = ...)` szignatúra is pontosítható `Path`-ra.

**Javítás:** `from pathlib import Path` felvétele; `chunks_path: Any` → `chunks_path: Path`.

**Teszt:** `npx`/`pytest` szinten elég, hogy a meglévő tesztek zöldek; opcionális: `get_type_hints(backend.retrieval._get_chunks)` nem dob.

---

## 12. `id()`-alapú cache-kulcs a reference resolutionben — kicsi

**Hely:** `backend/reference_resolution.py:8-13` (`_cache_key = (id(chunks), len(chunks))`).

**Tünet:** GC utáni id-újrahasznosítás stale doc-/paragrafus-indexet adhat; reindexenként a régi bejegyzések szivárognak (a `refresh_chunk_cache` ezeket nem üríti).

**Javítás:** a cache-eket a chunk-cache életciklusához kötni: `refresh_chunk_cache()` hívjon egy új `reference_resolution.clear_caches()`-t; a kulcs maradhat `id()`-alapú, de a cache-ek méretét 1-re korlátozzuk (mindig csak az aktuális korpusz indexe él).

**Regressziós teszt:** két különböző chunk-lista egymás után → a második hívás a második lista indexét adja; `clear_caches()` után a cache üres.

---

## 13. `set` kerül a cache-elt chunk dictekbe — kicsi

**Hely:** `preprocessing/index.py:61-67` (`_chunk_token_set` → `chunk["_token_set_cache"] = tokens`).

**Tünet:** A közös, cache-elt chunk-objektumokba JSON-serializálhatatlan `set` íródik. Ma latens (a reindex friss `load_chunks`-szal dolgozik), de az `index_chunks` `payload = dict(chunk)`-ot tárol — ha valaha a memóriabeli cache-elt chunkok mennek indexelésre vagy JSON-ba, törik.

**Javítás:** a token-set cache **ne a chunk dictben** éljen: modul-szintű `WeakValueDictionary`/dict `chunk_id → frozenset` formában; VAGY az `index_chunks` payload-építése explicit szűrje a `_` prefixű kulcsokat (defenzív réteg mindkettő mellett is indokolt).

**Regressziós teszt:** `_chunk_token_set` hívás után `json.dumps(chunk)` nem dob; `index_chunks` payloadjában nincs `_token_set_cache`.

---

## 14. `auto_merge_siblings` a limit-vágás után fut, pótlás nélkül — kicsi

**Hely:** `backend/retrieval.py:332-333` (`primary = primary[:limit]` után `auto_merge_siblings`).

**Tünet:** A testvér-leaf-ek szülőbe olvasztása a vágás után dedupol, így a végeredmény kevesebb lehet, mint `limit` elsődleges találat (information loss a draft forrásainál).

**Javítás:** a merge a vágás ELŐTT, a candidate-poolon fusson, és utána vágjunk `limit`-re — így a felszabaduló helyekre a következő jelöltek lépnek be.

**Regressziós teszt:** 5 találatból 3 testvér ugyanazon szülő alatt → merge után is `len(primary) == limit` (a pool következő elemeivel feltöltve).

---

## 15. `embed_documents` csendes `None`-szűrése — kicsi

**Hely:** `preprocessing/embedding.py:140` (`[v for v in results if v is not None]`).

**Tünet:** Hibás állapotban (kimaradt batch) a szűrés index-eltolódást okozna — a vektorok nem a szövegeikhez tartoznának. Ma az `index_chunks` `strict=True` zip-je elkapja, az `embed_query` IndexError-t adna; de a hibajelzés véletlenszerű, nem szándékolt.

**Javítás:** a szűrő helyett explicit ellenőrzés: `if any(v is None for v in results): raise RuntimeError("embedding batch incomplete")` — a hiba a keletkezés helyén, érthető üzenettel jelenjen meg.

**Regressziós teszt:** mockolt `_openai_embed`, ami kevesebb vektort ad vissza → `RuntimeError` (nem csendes lista-zsugorodás).

---

## Megjegyzések (nem bug, de döntést igényel)

- **`rewrite_query` latencia:** LLM-hívás a hot path-ban env-kapcsoló nélkül (~15–20 s plusz); az `LLM_VERIFY_ENABLED` mintájára `LLM_REWRITE_ENABLED` flag javasolt.
- **Hiányzó `service_provider`:** ha a hívó nem ad szolgáltatót, a retrieval szűretlenül keveri a négy szolgáltató dokumentumait (guardrails §5 kockázat). Javaslat: kötelező paraméter az agent-úton, vagy explicit warning a `retrieve` válaszában.

## Javasolt ütemezés

1. **1. kör (üzleti kockázat):** #1, #3, #4 — kis diffek, azonnali kockázatcsökkentés.
2. **2. kör (üzemeltetés):** #2 (+ a hozzá tartozó `force`-átvezetés), #9.
3. **3. kör (audit-konzisztencia):** #5, #6, #7, #8, #10.
4. **4. kör (technikai adósság):** #11–#15 + a két megjegyzés döntése.

Minden kör külön ágon, körönként egy PR; minden javítás előtt a reprodukáló teszt írandó meg (piros → zöld).
