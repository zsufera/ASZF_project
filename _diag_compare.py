"""For the failing cases: compare rewritten-query vs raw-query retrieval quality."""
import json, logging, glob, os
logging.basicConfig(level=logging.WARNING)

from backend.query_rewrite import rewrite_query, _fallback_query
from backend.retrieval import retrieve
from backend.masking import mask_text

FAILING = ["email-005-lefedettseg-one", "email-007-adatvedelem-one",
           "email-008-szamlazas-invitech", "email-009-hiba-helyi-kabeles"]

def show(label, res):
    print(f"  [{label}] mode={res.get('retrieval_mode')} n={res.get('result_count')}")
    for c in res.get("chunks", [])[:6]:
        q = (c.get("quote") or "")[:70].replace("\n", " ")
        print(f"      para={str(c.get('paragrafus')):8} score={c.get('score')} src={c.get('retrieval_source'):16} | {q}")

for cid in FAILING:
    f = f"data/sample_emails/{cid}.json"
    d = json.load(open(f, encoding="utf-8"))
    cat = d["varht_kategoria"]
    prov = d.get("szolgaltato")
    masked = mask_text(cid, d["torzs"])["masked_text"]

    print("=" * 100)
    print(f"{cid}  cat={cat} provider={prov}")
    print("  RAW masked msg:", masked[:120].replace("\n", " "))

    rq = rewrite_query(masked, cat)
    print("  REWRITTEN query:", rq)
    show("REWRITTEN", retrieve(query=rq, service_provider=prov, limit=5, category=cat))

    show("RAW-msg", retrieve(query=masked, service_provider=prov, limit=5, category=cat))

    fb = _fallback_query(masked, cat)
    show("RULE-FALLBACK", retrieve(query=fb, service_provider=prov, limit=5, category=cat))
