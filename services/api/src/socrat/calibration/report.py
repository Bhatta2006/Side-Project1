"""Calibration report in Markdown (M7 task 31).

Aggregates only: counts, shares and item keys. Nothing here reads users, enrollments or any
per-learner row beyond counting responses, so the report contains no personal data.
"""

from collections import Counter, defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.calibration import stats
from socrat.catalog.registry import Catalog
from socrat.models import ItemCalibration, QuizResponse
from socrat.quiz import service as quiz

# §9.6 success zones (share correct) per track.
ZONES = {"foundations": (0.75, 0.85), "interview": (0.65, 0.80), "competitive": (0.50, 0.70)}
PATTERN_ATOMS = ("worked", "faded", "visualizer", "micro", "classify")


def _table(header: list[str], rows: list[list]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return lines


def _share(part: int, whole: int) -> str:
    return f"{part / whole:.0%}" if whole else "n/a"


def build(
    db: Session, catalog: Catalog, generated_at: str, rules: stats.Rules = stats.DEFAULT
) -> str:
    items = quiz.items_for(db, catalog)
    records = {r.item_id: r for r in db.scalars(select(ItemCalibration))}
    responses = dict(
        db.execute(select(QuizResponse.item_id, func.count()).group_by(QuizResponse.item_id)).all()
    )
    out = [
        "# Item calibration report",
        "",
        f"Generated {generated_at}. Aggregates only: no learner identifiers or answers appear here.",
        "",
        "## Item health",
        "",
    ]
    status = Counter(i.status for i in items)
    answered = [i for i in items if responses.get(i.key)]
    ready = [i for i in answered if responses[i.key] >= rules.min_responses]
    flagged = sorted((k, r) for k, r in records.items() if r.flags)
    out += _table(
        [
            "Items",
            "Provisional",
            "Calibrated",
            "Retired",
            "With responses",
            f"≥ {rules.min_responses} responses",
            "Flagged",
        ],
        [
            [
                len(items),
                status["provisional"],
                status["calibrated"],
                status["retired"],
                len(answered),
                len(ready),
                len(flagged),
            ]
        ],
    )
    if flagged:
        out += ["", "Flagged for repair:", ""]
        out += _table(
            ["Item", "Responses", "% correct", "Discrimination", "Median s", "Flags"],
            [
                [
                    f"`{k}`",
                    r.n_responses,
                    f"{(r.pct_correct or 0):.0%}",
                    "n/a" if r.discrimination is None else f"{r.discrimination:.2f}",
                    f"{(r.median_time_s or 0):.0f}",
                    ", ".join(r.flags),
                ]
                for k, r in flagged
            ],
        )
    approved = sorted((k, r) for k, r in records.items() if r.approved_by)
    out += ["", f"Human-approved status changes: {len(approved)}."]

    out += [
        "",
        "## Coverage per band",
        "",
        "Servable items (not retired) by course, band and pool.",
        "",
    ]
    coverage: dict[tuple[str, int], Counter[str]] = defaultdict(Counter)
    for item in items:
        if item.status != "retired":
            coverage[(item.concept.split(":")[0], item.band)][item.pool] += 1
    out += _table(
        ["Course", "Band", "Practice", "Assessment"],
        [
            [course, band, c["practice"], c["assessment"]]
            for (course, band), c in sorted(coverage.items())
        ],
    )
    out += ["", "Pilot patterns:", ""]
    rows = []
    for pid in sorted(catalog.patterns):
        mine = [i for i in items if i.pattern == pid and i.status != "retired"]
        bands = Counter(i.band for i in mine)
        rows.append([f"`{pid}`", len(mine)] + [bands.get(b, 0) for b in range(1, 8)])
    out += _table(["Pattern", "Items"] + [f"B{b}" for b in range(1, 8)], rows)

    out += [
        "",
        "## Success-zone share",
        "",
        f"Items with ≥ {rules.min_responses} responses whose percent correct falls in the track's zone (§9.6).",
        "",
    ]
    rows = []
    for track, (low, high) in ZONES.items():
        measured = [records[i.key] for i in ready if track == "foundations" and i.key in records]
        inside = sum(
            1 for r in measured if r.pct_correct is not None and low <= r.pct_correct <= high
        )
        rows.append(
            [track, f"{low:.0%}–{high:.0%}", len(measured), inside, _share(inside, len(measured))]
        )
    out += _table(["Track", "Zone", "Items", "In zone", "Share"], rows)

    out += ["", "## Atom gaps", ""]
    no_pack = sorted(c for c in catalog.concepts if c not in catalog.atom_packs)
    out.append(f"Concepts without an atom pack: {len(no_pack)} of {len(catalog.concepts)}.")
    if no_pack:
        out += ["", ", ".join(f"`{c}`" for c in no_pack)]
    rows = []
    for pid in sorted(catalog.patterns):
        pack = catalog.pattern_atoms.get(pid)
        kinds = {a.kind for a in pack.atoms} if pack else set()
        missing = [k for k in PATTERN_ATOMS if k not in kinds]
        rows.append([f"`{pid}`", pack.status if pack else "none", ", ".join(missing) or "none"])
    out += ["", "Pilot pattern packs:", ""] + _table(["Pattern", "Pack", "Missing atoms"], rows)

    out += ["", "## Provenance completeness", ""]
    counts = {
        "Concepts": [c.provenance is not None for c in catalog.concepts.values()],
        "Concept quiz items": [
            q.provenance is not None for c in catalog.concepts.values() for q in c.quiz
        ],
        "Problems": [p.provenance is not None for _, p in catalog.problems.values()],
        "Atom packs": [p.provenance is not None for p in catalog.atom_packs.values()],
        "Pattern atom packs": [p.provenance is not None for p in catalog.pattern_atoms.values()],
        "Patterns": [True for _ in catalog.patterns.values()],  # required by the schema
        "Quiz families": [True for _ in catalog.quiz_families.values()],  # required by the schema
    }
    reviewed = {
        "Patterns": sum(p.provenance.review is not None for p in catalog.patterns.values()),
        "Quiz families": sum(
            f.provenance.review is not None for f in catalog.quiz_families.values()
        ),
    }
    out += _table(
        ["Kind", "Records", "With provenance", "Share", "Human-reviewed"],
        [
            [
                kind,
                len(flags),
                sum(flags),
                _share(sum(flags), len(flags)),
                reviewed.get(kind, "n/a"),
            ]
            for kind, flags in counts.items()
        ],
    )
    return "\n".join(out) + "\n"
