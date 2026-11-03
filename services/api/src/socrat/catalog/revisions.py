"""Keep quiz ids resolvable when a concept is rewritten (master prompt 9.1, 10.4, 13; acceptance
criterion 15: progress survives course revisions).

A rewrite can return the same question with a new id, or drop a question. Stored attempts,
open quiz sessions, placements and weekly assessments all refer to items by id, so:

- a new item that is clearly the same question as an old one takes the old id (and its former
  ids) as ``former_ids``. "Clearly the same" is deterministic: the normalised prompt is equal,
  or the prompts are at least ``SIMILAR`` alike and the correct option's text is equal;
- an old item no new item answers to is moved to ``retired_quiz``: never offered again, but
  ``Concept.quiz_item`` still finds it, so nothing in flight breaks.

No model and no network. ``coursegen.maintain.lost_ids`` stays the report of what a rewrite
*would* orphan before this runs; after it runs that list is empty for quiz items.
"""

import re
from difflib import SequenceMatcher

from socrat.catalog.schema import Concept, QuizItem

SIMILAR = 0.85
MAX_RETIRED = 40


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.lower())).strip()


def _answer(q: QuizItem) -> str:
    # Case and spacing only: in code answers the symbols are the answer (a & b vs a | b).
    text = q.options[q.answer] if q.answer < len(q.options) else ""
    return re.sub(r"\s+", " ", text.lower()).strip()


def same_question(old: QuizItem, new: QuizItem) -> float:
    """A match score in [0, 1]; 0 when the two are not the same question."""
    a, b = _norm(old.prompt), _norm(new.prompt)
    if a == b:
        return 1.0
    ratio = SequenceMatcher(None, a, b).ratio()
    return ratio if ratio >= SIMILAR and _answer(old) == _answer(new) else 0.0


def carry(old: Concept | None, new: Concept) -> Concept:
    """``new`` with quiz ids carried over from ``old`` and dropped items retired."""
    if old is None:
        return new
    previous = [*old.quiz]
    live = list(new.quiz)
    claimed = {i for q in live for i in (q.id, *q.former_ids)}

    # Best matches first, each old item to at most one new item.
    pairs = sorted(
        (
            (same_question(o, n), oi, ni)
            for oi, o in enumerate(previous)
            for ni, n in enumerate(live)
            if not o.matches(n.id)
        ),
        key=lambda t: (-t[0], t[1], t[2]),
    )
    used_old: set[int] = set()
    for score, oi, ni in pairs:
        if score <= 0 or oi in used_old:
            continue
        o = previous[oi]
        ids = [i for i in (o.id, *o.former_ids) if i not in claimed]
        if not ids and o.id in claimed:
            used_old.add(oi)  # already answered to by some new item
            continue
        live[ni] = live[ni].model_copy(update={"former_ids": [*live[ni].former_ids, *ids]})
        claimed.update(ids)
        used_old.add(oi)

    retired = [q for q in old.retired_quiz if q.id not in claimed]
    for o in previous:
        if o.id not in claimed:
            retired.append(
                o.model_copy(update={"former_ids": [i for i in o.former_ids if i not in claimed]})
            )
    seen: set[str] = set()
    unique = []
    for q in reversed(retired):  # newest retirement wins, keep the most recent MAX_RETIRED
        if q.id not in seen:
            seen.add(q.id)
            unique.append(q)
    retired = list(reversed(unique))[-MAX_RETIRED:]
    return new.model_copy(update={"quiz": live, "retired_quiz": retired})


def module_version(course, module) -> str:
    """A module's own version (master prompt 4, 13: course, module and activity versioned
    independently). Derived from the module's definition and each of its concepts' content
    (status, content version, quiz ids, sequence), so it changes exactly when the module does,
    and two modules can change independently. Activities carry their own version in
    ``Provenance.version``; the course its ``version``."""
    import hashlib
    import json

    by_id = {c.id: c for c in course.concepts}
    parts = [module.model_dump(mode="json")]
    for cid in module.concepts:
        c = by_id.get(cid)
        if c is None:
            continue
        parts.append(
            [
                c.id,
                c.status,
                c.provenance.version if c.provenance else 0,
                [q.id for q in c.quiz],
                c.sequence,
                len(c.lesson),
            ]
        )
    digest = hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()
    return f"m-{digest[:10]}"
