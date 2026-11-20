"""Item calibration (Content Master Plan §8.7).

    uv run python scripts/content/calibrate.py stats
    uv run python scripts/content/calibrate.py set-status <item> --to calibrated --approver "Full Name"
    uv run python scripts/content/calibrate.py report --out calibration-report.md

``stats`` recomputes item health and flags; it never changes a status. ``set-status`` is the
only way to change one, and it needs the name of the person approving: calibration also needs
at least 30 responses and no repair flags. The database comes from the usual SOCRAT_ settings
(SOCRAT_DATABASE_URL), or --database-url.
"""

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "services/api/src"), str(ROOT / "services/execution/src")]

from sqlalchemy.orm import Session  # noqa: E402

from socrat.calibration import job, report  # noqa: E402
from socrat.catalog.registry import CONTENT_ROOT, load  # noqa: E402
from socrat.config import DatabaseSettings  # noqa: E402
from socrat.database import make_engine  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--database-url", default=None)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("stats", help="recompute item statistics and repair flags")
    change = commands.add_parser("set-status", help="change one item's status (needs a person)")
    change.add_argument("item")
    change.add_argument("--to", required=True, choices=["calibrated", "retired", "provisional"])
    change.add_argument("--approver", required=True, help="full name of the person approving")
    out = commands.add_parser("report", help="write the Markdown calibration report")
    out.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    url = args.database_url or DatabaseSettings().database_url_value
    engine = make_engine(url)
    catalog = load(Path(os.environ.get("SOCRAT_CONTENT_ROOT", CONTENT_ROOT)), tests_root=None)
    try:
        with Session(engine) as db, db.begin():
            if args.command == "stats":
                computed = job.run(db, catalog)
                flagged = {k: list(v.flags) for k, v in computed.items() if v.flags}
                print(json.dumps(dict(items=len(computed), flagged=flagged), indent=2))
            elif args.command == "set-status":
                try:
                    record = job.transition(db, args.item, args.to, args.approver, int(time.time()))
                except job.TransitionError as exc:
                    print(f"Refused: {exc}", file=sys.stderr)
                    return 1
                print(f"{record.item_id}: {record.status} (approved by {record.approved_by})")
            else:
                stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
                text = report.build(db, catalog, stamp)
                if args.out:
                    args.out.write_text(text, encoding="utf-8", newline="\n")
                    print(f"Wrote {args.out}")
                else:
                    print(text)
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
