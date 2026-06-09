from __future__ import annotations

from fastapi import APIRouter

from backend.knowledge_service import knowledge_search, knowledge_section, knowledge_tree
from backend.metadata import response_meta


router = APIRouter()


@router.get("/aszf/tree")
def aszf_tree(limit: int = 250) -> dict:
    items = knowledge_tree(limit=limit)
    return {**response_meta(), "items": items, "count": len(items)}


@router.get("/aszf/section/{chunk_id}")
def aszf_section(chunk_id: str) -> dict:
    item = knowledge_section(chunk_id)
    if not item:
        return {**response_meta(), "error": "ASZF szakasz nem talalhato", "chunk_id": chunk_id}
    return {**response_meta(), "item": item}


@router.get("/aszf/search")
def aszf_search(q: str, limit: int = 20) -> dict:
    items = knowledge_search(q, limit=limit)
    return {**response_meta(), "items": items, "count": len(items)}
