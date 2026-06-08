from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from preprocessing.derive_params import derive_all
from preprocessing.embedding import active_mode, vector_size
from preprocessing.index import DEFAULT_CHUNKS_PATH, index_chunks, load_chunks
from preprocessing.manifest import DEFAULT_OUTPUT_PATH, build_manifest, write_manifest
from preprocessing.parse import DEFAULT_CHUNKS_OUTPUT, DEFAULT_PAGES_OUTPUT, parse_and_chunk


def run_reindex(force: bool = False) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc).isoformat()
    items = build_manifest()
    write_manifest(items, DEFAULT_OUTPUT_PATH)
    page_count, chunk_count = parse_and_chunk(
        manifest_path=DEFAULT_OUTPUT_PATH,
        pages_output=DEFAULT_PAGES_OUTPUT,
        chunks_output=DEFAULT_CHUNKS_OUTPUT,
    )

    indexed_chunks = 0
    qdrant_status = "skipped"
    chunks = load_chunks(DEFAULT_CHUNKS_PATH)
    try:
        indexed_chunks = index_chunks(chunks=chunks)
        qdrant_status = "ok"
    except Exception as exc:
        qdrant_status = f"failed: {exc}"

    derive_report = derive_all()

    manifest = json.loads(DEFAULT_OUTPUT_PATH.read_text(encoding="utf-8"))
    versions = sorted(
        {
            item.get("version_hint")
            for item in manifest.get("documents", [])
            if item.get("version_hint")
        },
        reverse=True,
    )
    finished_at = datetime.now(timezone.utc).isoformat()
    return {
        "aszf_version": versions[0] if versions else None,
        "indexed_docs": manifest.get("document_count", 0),
        "indexed_chunks": chunk_count,
        "indexed_qdrant_chunks": indexed_chunks,
        "parsed_pages": page_count,
        "qdrant_status": qdrant_status,
        "embedding_mode": active_mode(),
        "embedding_dim": vector_size(),
        "derive_report": {
            "mandatory_ref_categories": derive_report.get("mandatory_ref_categories"),
            "escalation_trigger_count": derive_report.get("escalation_trigger_count"),
        },
        "force": force,
        "started_at": started_at,
        "finished_at": finished_at,
    }
