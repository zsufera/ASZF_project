from __future__ import annotations

import argparse
import subprocess
import sys

from backend.acceptance_service import run_acceptance


def main() -> int:
    parser = argparse.ArgumentParser(description="POC minőség-kapu: pytest + acceptance.")
    parser.add_argument("--skip-pytest", action="store_true")
    parser.add_argument("--eval-limit", type=int, default=10)
    parser.add_argument("--no-edge", action="store_true")
    parser.add_argument("--no-demo", action="store_true")
    args = parser.parse_args()

    if not args.skip_pytest:
        result = subprocess.run([sys.executable, "-m", "pytest", "-q"], check=False)
        if result.returncode != 0:
            print("pytest FAILED")
            return result.returncode

    acceptance = run_acceptance(
        eval_limit=args.eval_limit,
        include_edge=not args.no_edge,
        run_demo=not args.no_demo,
    )
    print(f"acceptance passed={acceptance['passed']}")
    if acceptance["kpi_failures"]:
        print("KPI failures:", *acceptance["kpi_failures"], sep="\n  ")
    if acceptance["demo_failures"]:
        print("Demo failures:", *acceptance["demo_failures"], sep="\n  ")
    return 0 if acceptance["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
