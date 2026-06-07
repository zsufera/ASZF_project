from __future__ import annotations

import argparse
import json
from pathlib import Path

from preprocessing.index import load_chunks, search_chunks
from preprocessing.manifest import build_manifest, write_manifest
from preprocessing.parse import parse_and_chunk


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local ingest smoke: manifest -> parse/chunk -> retrieve.")
    parser.add_argument("--manifest", default="data/ingest_manifest.json")
    parser.add_argument("--pages-output", default="data/processed/parsed_pages.jsonl")
    parser.add_argument("--chunks-output", default="data/processed/chunks.jsonl")
    parser.add_argument("--query", default="számlázási kifogás")
    parser.add_argument("--service-provider", default="ONE")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    chunks_output = Path(args.chunks_output)

    manifest_items = build_manifest()
    write_manifest(manifest_items, manifest_path)
    page_count, chunk_count = parse_and_chunk(
        manifest_path=manifest_path,
        pages_output=Path(args.pages_output),
        chunks_output=chunks_output,
    )
    results = search_chunks(
        query=args.query,
        chunks=load_chunks(chunks_output),
        service_provider=args.service_provider,
        limit=5,
    )

    print(
        json.dumps(
            {
                "documents": len(manifest_items),
                "pages": page_count,
                "chunks": chunk_count,
                "query": args.query,
                "service_provider": args.service_provider,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
