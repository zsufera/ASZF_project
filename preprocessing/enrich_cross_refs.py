from __future__ import annotations

import argparse
import json
from pathlib import Path

from preprocessing.parse import extract_references

DEFAULT_CHUNKS_PATH = Path("data/processed/chunks.jsonl")


def enrich_chunks_file(path: Path = DEFAULT_CHUNKS_PATH) -> int:
    """A chunks.jsonl minden sorának cross_refs-ét újraszámolja a text-ből (strukturált).

    Visszaadja a feldolgozott sorok számát. A meglévő (régi formátumú) cross_refs felülíródik.
    """
    if not path.exists():
        return 0
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    for row in rows:
        row["cross_refs"] = extract_references(row.get("text", ""))
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill structured cross_refs into chunks.jsonl from text.")
    parser.add_argument("--chunks", default=str(DEFAULT_CHUNKS_PATH))
    args = parser.parse_args()
    count = enrich_chunks_file(Path(args.chunks))
    print(f"Enriched {count} chunk(s) with structured cross_refs.")


if __name__ == "__main__":
    main()
