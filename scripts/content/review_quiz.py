"""Human review of quiz families (Content Master Plan §8.7).

    uv run python scripts/content/review_quiz.py status
    uv run python scripts/content/review_quiz.py next --by "Full Name" [--course dsa] [--limit 5]

Items from a family count as mastery evidence only once a person has read the family and
signed it off. ``next`` shows unreviewed families one at a time (every static item with its
answer and explanation, and a few verified drafts of a generator) and asks y / n / q. Only a
"y" typed by the reviewer writes ``provenance.review`` with their name and today's date;
there is deliberately no bulk or non-interactive approval.
"""

import argparse
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "services/api/src"), str(ROOT / "services/execution/src")]

from socrat.catalog.registry import CONTENT_ROOT, load  # noqa: E402

QUIZ_ROOT = CONTENT_ROOT.parent / "quiz"
SAMPLE_DRAFTS = 3


def family_files() -> dict[str, Path]:
    out = {}
    for path in sorted(QUIZ_ROOT.rglob("*.yaml")):
        match = re.search(r"^id:\s*(\S+)", path.read_text(encoding="utf-8"), re.M)
        if match:
            out[match.group(1)] = path
    return out


def letter(i: int) -> str:
    return "ABCDEFGH"[i]


def show(catalog, family) -> None:
    print(f"\n=== {family.id}  ({family.concept}, {family.format})")
    for q in family.items:
        print(f"\n[{q.id}] band {q.band}: {q.prompt}")
        for lang, code in (q.code or {}).items():
            print(f"  --- {lang}\n" + "\n".join("    " + line for line in code.splitlines()))
        for i, option in enumerate(q.options):
            mark = "*" if i == q.answer else " "
            print(f"  {mark} {letter(i)}. {option}")
        print(f"  why: {q.explanation}")
    if family.generator is not None and catalog.quiz_root is not None:
        from socrat.quiz.generate import framework

        manifest = framework.load_manifest(catalog.quiz_root)
        drafts = list(framework.verified_drafts(catalog.quiz_root, family, manifest))
        print(f"\n  generator: {len(drafts)} verified drafts; first {SAMPLE_DRAFTS}:")
        for seed, _pool, draft in drafts[:SAMPLE_DRAFTS]:
            print(f"\n  [seed {seed}] band {draft.band}: {draft.prompt}")
            for i, option in enumerate(draft.options):
                print(f"    {'*' if i == draft.answer else ' '} {letter(i)}. {option.text}")
            print(f"    why: {draft.explanation}")


def stamp(path: Path, by: str) -> None:
    text = path.read_text(encoding="utf-8")
    review = f"  review:\n    by: {by}\n    at: '{date.today().isoformat()}'\n"
    if re.search(r"^provenance:\s*$", text, re.M):
        text = re.sub(r"^provenance:\s*\n", "provenance:\n" + review, text, count=1, flags=re.M)
    else:
        text = text.rstrip("\n") + "\nprovenance:\n" + review
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="reviewed and unreviewed families per course")
    nxt = commands.add_parser("next", help="review unreviewed families one at a time")
    nxt.add_argument("--by", required=True, help="full name of the person reviewing")
    nxt.add_argument("--course", default=None)
    nxt.add_argument("--limit", type=int, default=5)
    args = parser.parse_args(argv)

    catalog = load()
    families = sorted(catalog.quiz_families.values(), key=lambda f: f.id)
    if args.command == "status":
        done, todo = Counter(), Counter()
        for f in families:
            course = f.concept.split(":", 1)[0]
            (done if f.provenance.review is not None else todo)[course] += 1
        for course in sorted(set(done) | set(todo)):
            print(f"{course}: {done[course]} reviewed, {todo[course]} waiting")
        return 0

    if len(args.by.split()) < 2:
        parser.error("--by needs the reviewer's full name")
    if not sys.stdin.isatty():
        parser.error("review is interactive: run it in a terminal")
    files = family_files()
    queue = [
        f
        for f in families
        if f.provenance.review is None
        and f.status != "retired"
        and (args.course is None or f.concept.startswith(args.course + ":"))
    ]
    print(f"{len(queue)} families waiting; showing up to {args.limit}.")
    for family in queue[: args.limit]:
        show(catalog, family)
        answer = input("\nApprove this family? [y]es / [n]o, skip / [q]uit: ").strip().lower()
        if answer == "q":
            break
        if answer == "y":
            stamp(files[family.id], args.by)
            print(f"  signed off by {args.by}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
