"""Measure non-determinism: same sources, run synthesize N times, count llm vs insufficient."""
import logging
logging.basicConfig(level=logging.WARNING)

from backend.query_rewrite import rewrite_query
from backend.retrieval import retrieve
from backend.policy_map import build_policy_map
from backend.draft import synthesize_answer

MSG = "Fel szeretném mondani a vezetékes internet szerződésemet, mennyi a felmondási idő és van-e hűségidő?"
CATEGORY = "szerzodesfelmondas_modositas"

q = rewrite_query(MSG, CATEGORY)
res = retrieve(query=q, service_provider="ONE", limit=5, category=CATEGORY)
pm = build_policy_map(category=CATEGORY, chunks=res.get("chunks", []))
print("query:", q)
print("sources:", len(pm.get("policy_items", [])), "scores:",
      [it.get("score") for it in pm.get("policy_items", [])])

N = 8
modes = []
for i in range(N):
    d = synthesize_answer(case_id=f"FLIP-{i}", category=CATEGORY, channel="email",
                          output_mode="hitl", policy_map=pm, actions=[], input_text_masked=MSG)
    modes.append(d.get("generation_mode"))
    print(f"run {i}: {d.get('generation_mode')}")

from collections import Counter
print("DISTRIBUTION:", Counter(modes))
