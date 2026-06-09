"""Run every sample email through the full agent and report generation_mode + retrieval stats."""
import json, logging, glob, os
logging.basicConfig(level=logging.WARNING)

from agent.runner import run_agent

files = sorted(glob.glob("data/sample_emails/email-*.json"))
print(f"{'case':40} {'category':32} {'mode':12} {'retr':5} {'pol':4} {'esc'}")
print("-" * 110)
for f in files:
    d = json.load(open(f, encoding="utf-8"))
    try:
        r = run_agent(
            case_id=d["email_id"],
            channel="email",
            input_text=d["torzs"],
            service_provider=d.get("szolgaltato"),
            sender_email=d.get("felado_email"),
            output_mode="hitl",
        )
        cat = r.get("classification", {}).get("category", "?")
        mode = r.get("draft", {}).get("generation_mode", "?")
        retr = r.get("retrieval", {}).get("result_count", "?")
        pol = len(r.get("policy_map", {}).get("policy_items", []))
        esc = r.get("escalation", {}).get("required")
        flag = "  <-- INSUFFICIENT" if mode == "insufficient" else ""
        print(f"{os.path.basename(f):40} {cat:32} {mode:12} {str(retr):5} {str(pol):4} {str(esc)}{flag}")
    except Exception as e:
        print(f"{os.path.basename(f):40} ERROR: {e}")
