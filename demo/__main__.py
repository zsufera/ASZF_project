from __future__ import annotations

import json

from demo.runner import run_all_scenarios


def main() -> None:
    report = run_all_scenarios(save_report=True)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
