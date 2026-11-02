"""Verify every generated quiz item by execution and write ``content/quiz/verified.json``.

    uv run python scripts/content/validate_quiz.py            # verify and write the manifest
    uv run python scripts/content/validate_quiz.py --check    # verify; fail if the manifest is stale

Only items listed in the manifest with the current source digest reach learners. The run
fails when any seed is rejected, so a broken generator cannot ship.
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "services/api/src"), str(ROOT / "services/execution/src")]

from runner.toolchains import toolchains  # noqa: E402

from socrat.catalog import atoms  # noqa: E402
from socrat.catalog.registry import CONTENT_ROOT, load  # noqa: E402
from socrat.quiz.generate import framework, mutate, verify  # noqa: E402
from socrat.quiz.generate.harness import Runner  # noqa: E402


def check_defects(root: Path, families, taxonomy: set[str]) -> list[str]:
    """Generators that declare DEFECTS must name defects from the catalogue."""
    problems = []
    catalogue = mutate.load(root, taxonomy) if (root / "defects.yaml").exists() else None
    for family in families:
        declared = getattr(framework.module(root, family.generator), "DEFECTS", {})
        for defect_id in declared:
            if catalogue is None:
                problems.append(f"{family.id}: defect {defect_id} but no defects.yaml")
                continue
            try:
                catalogue.get(defect_id)
            except KeyError:
                problems.append(f"{family.id}: unknown defect {defect_id}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="do not write; fail when stale")
    parser.add_argument(
        "--only", help="verify only families whose id contains this text; merge into the manifest"
    )
    args = parser.parse_args(argv)

    catalog = load(CONTENT_ROOT, tests_root=None)
    root = catalog.quiz_root
    assert root is not None
    taxonomy = atoms.load_taxonomy(CONTENT_ROOT.parent / "atoms")
    families = [f for f in catalog.quiz_families.values() if f.generator is not None]
    if args.only:
        families = [f for f in families if args.only in f.id]
    tools = toolchains()
    needed = {lang for f in families for lang in f.languages}
    missing = sorted(needed - set(tools))
    if missing:
        print(f"Toolchains missing: {', '.join(missing)} (run scripts\\dev\\doctor.ps1)")
        return 2
    problems = check_defects(root, families, taxonomy)
    runner = Runner(tools)
    manifest: dict = {}
    if args.only and (root / framework.MANIFEST).exists():
        manifest = json.loads((root / framework.MANIFEST).read_text(encoding="utf-8"))
    report = []
    started = time.monotonic()
    for family in sorted(families, key=lambda f: f.id):
        verdicts = verify.verify_family(root, family, runner, taxonomy)
        entry = verify.manifest_entry(root, family, verdicts)
        manifest[family.id] = entry
        report.append(
            dict(
                family=family.id,
                verified=len(entry["items"]),
                duplicates=len(entry["duplicates"]),
                rejected=len(entry["rejected"]),
            )
        )
        for seed, why in list(entry["rejected"].items())[:5]:
            problems.append(f"{family.id} seed {seed}: {'; '.join(why)}")
    path = root / framework.MANIFEST
    text = json.dumps(manifest, indent=1, sort_keys=True) + "\n"
    stale = not path.exists() or json.loads(path.read_text(encoding="utf-8")) != manifest
    if args.check and stale:
        problems.append(f"{path.relative_to(ROOT)} is stale: run scripts/content/validate_quiz.py")
    if not args.check and not problems:
        path.write_text(text, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            dict(
                families=report,
                items=sum(r["verified"] for r in report),
                seconds=round(time.monotonic() - started, 1),
                problems=problems,
            ),
            indent=2,
        )
    )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
