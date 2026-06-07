from __future__ import annotations

import argparse
import json

from backend.eval_service import run_eval


def main() -> None:
    parser = argparse.ArgumentParser(description="Run reference-free eval on sample emails.")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    report = run_eval(limit=args.limit)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
