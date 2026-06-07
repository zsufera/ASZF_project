from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.retrieval import retrieve
from preprocessing.index import DEFAULT_CHUNKS_PATH


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test local retrieval from chunks.jsonl.")
    parser.add_argument("query", help="Query text to search for.")
    parser.add_argument("--chunks", default=str(DEFAULT_CHUNKS_PATH))
    parser.add_argument("--service-provider", default=None)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    result = retrieve(
        query=args.query,
        service_provider=args.service_provider,
        limit=args.limit,
        chunks_path=Path(args.chunks),
        prefer_qdrant=False,
    )
    print(
        json.dumps(
            {
                "query": args.query,
                "retrieval_mode": result.get("retrieval_mode"),
                "results": result.get("chunks", []),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
