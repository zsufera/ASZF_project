"""Diagnostic: trace the retrieval->policy->synthesis chain to find WHERE coverage collapses."""
import logging
logging.basicConfig(level=logging.INFO)

from preprocessing.embedding import active_mode
from backend.llm import llm_available
from backend.query_rewrite import rewrite_query
from backend.retrieval import retrieve
from backend.policy_map import build_policy_map
from backend.draft import _build_sources, synthesize_answer

MSG = "Fel szeretném mondani a vezetékes internet szerződésemet, mennyi a felmondási idő és van-e hűségidő?"
CATEGORY = "szerzodesfelmondas_modositas"
PROVIDER = "ONE"

print("=== BOUNDARY 0: environment ===")
print("active_mode (embedding):", active_mode())
print("llm_available:", llm_available())

print("\n=== BOUNDARY 1: query rewrite ===")
q = rewrite_query(MSG, CATEGORY)
print("rewritten query:", repr(q))

print("\n=== BOUNDARY 2: retrieve() ===")
res = retrieve(query=q, service_provider=PROVIDER, limit=5, category=CATEGORY)
print("retrieval_mode:", res.get("retrieval_mode"))
print("result_count:", res.get("result_count"))
print("unresolved_refs:", len(res.get("unresolved_refs", [])))
for c in res.get("chunks", []):
    print(f"  - id={c.get('chunk_id')} para={c.get('paragrafus')} score={c.get('score')} src={c.get('retrieval_source')} doc={c.get('dok_cim')}")

print("\n=== BOUNDARY 2b: retrieve WITHOUT provider filter ===")
res2 = retrieve(query=q, service_provider=None, limit=5, category=CATEGORY)
print("retrieval_mode:", res2.get("retrieval_mode"), "result_count:", res2.get("result_count"))
for c in res2.get("chunks", [])[:5]:
    print(f"  - id={c.get('chunk_id')} para={c.get('paragrafus')} score={c.get('score')} src={c.get('retrieval_source')}")

print("\n=== BOUNDARY 3: build_policy_map ===")
pm = build_policy_map(category=CATEGORY, chunks=res.get("chunks", []))
items = pm.get("policy_items", [])
print("policy_items count:", len(items))
print("missing_mandatory:", pm.get("missing_mandatory"))
for it in items:
    print(f"  - chunk_id={it.get('chunk_id')} para={it.get('paragrafus')} idezet_len={len(str(it.get('idezet','')))}")

print("\n=== BOUNDARY 4: _build_sources ===")
sources = _build_sources(items)
print("sources count:", len(sources))

print("\n=== BOUNDARY 5: synthesize_answer (email) ===")
draft = synthesize_answer(case_id="DIAG-1", category=CATEGORY, channel="email",
                          output_mode="hitl", policy_map=pm, actions=[], input_text_masked=MSG)
print("generation_mode:", draft.get("generation_mode"))
print("body (first 200):", draft.get("body_masked", "")[:200])
