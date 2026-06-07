from __future__ import annotations

import argparse
import json

from backend.eval_service import run_eval


def main() -> None:
    parser = argparse.ArgumentParser(description="Run reference-free eval harness on sample emails.")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--category", type=str, default=None)
    parser.add_argument("--service-provider", type=str, default=None)
    parser.add_argument("--no-edge", action="store_true")
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()

    report = run_eval(
        limit=args.limit,
        category=args.category,
        service_provider=args.service_provider,
        include_edge=not args.no_edge,
        save_report=not args.no_save,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
