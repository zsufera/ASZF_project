from __future__ import annotations

import argparse
import json
from pathlib import Path

from preprocessing.index import DEFAULT_CHUNKS_PATH, load_chunks, search_chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test local retrieval from chunks.jsonl.")
    parser.add_argument("query", help="Query text to search for.")
    parser.add_argument("--chunks", default=str(DEFAULT_CHUNKS_PATH))
    parser.add_argument("--service-provider", default=None)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    chunks = load_chunks(Path(args.chunks))
    results = search_chunks(
        query=args.query,
        chunks=chunks,
        service_provider=args.service_provider,
        limit=args.limit,
    )
    print(json.dumps({"query": args.query, "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
