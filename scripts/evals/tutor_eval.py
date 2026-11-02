"""Run the tutor evaluation scenarios against the configured AI provider.

    uv run python scripts/evals/tutor_eval.py            # provider from .env / SOCRAT_AI_*
    uv run python scripts/evals/tutor_eval.py --json     # machine-readable report

Exits non-zero when any scenario fails, so it can gate prompt or model changes.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "api" / "src"))

from socrat.assistant import evals  # noqa: E402
from socrat.assistant.gateway import make_provider  # noqa: E402
from socrat.catalog.registry import default_catalog  # noqa: E402
from socrat.config import Settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    parser.add_argument("--only", help="run one scenario by name")
    parser.add_argument(
        "--require-provider",
        action="store_true",
        help="exit 2 when only the offline provider is configured (a scheduled run must not "
        "pass by grading canned replies)",
    )
    args = parser.parse_args()
    settings = Settings()
    if args.require_provider and settings.ai_provider == "offline":
        print("No AI provider configured (SOCRAT_AI_PROVIDER=offline); nothing to evaluate.")
        return 2
    scenarios = [s for s in evals.SCENARIOS if not args.only or s.name == args.only]
    report = asyncio.run(evals.run(default_catalog(), settings, make_provider(settings), scenarios))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for row in report:
            mark = "PASS" if row["passed"] else "FAIL"
            print(f"{mark}  {row['scenario']}  tools={row['tools']}  provider={row['provider']}")
            for failure in row["failures"]:
                print(f"      - {failure}")
        passed = sum(r["passed"] for r in report)
        print(f"\n{passed}/{len(report)} scenarios passed")
    return 0 if all(r["passed"] for r in report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
