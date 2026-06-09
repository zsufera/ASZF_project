from __future__ import annotations

from typing import Any

from backend import llm_tasks
from backend.policy_map import build_policy_map
from backend.retrieval import retrieve


def retrieve_for_case(
    text_masked: str,
    category: str,
    service_provider: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    rewrite = llm_tasks.rewrite_query_task(text_masked, category)
    search_query = rewrite["result"][:400]
    retrieval = retrieve(
        query=search_query,
        service_provider=service_provider,
        limit=limit,
        category=category,
    )
    chunks = retrieval.get("chunks", [])
    policy_map = build_policy_map(category=category, chunks=chunks)
    return {
        "search_query": search_query,
        "chunks": chunks,
        "result_count": retrieval.get("result_count", 0),
        "unresolved_refs": retrieval.get("unresolved_refs", []),
        "policy_map": policy_map,
        "rewrite_mode": rewrite["mode"],
    }
