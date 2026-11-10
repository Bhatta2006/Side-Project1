"""A practice bank for any course, built from what its lessons already hold.

Practice sets used to be written on demand by one model call each: slow, capped per day,
unchecked, and the same five kinds for every subject. A released lesson already carries
material that passed the code gates and the fact check: its in-lesson checks, and the rows it
adds to the course's own sections (a language's vocabulary, a history course's timeline, a
music course's repertoire). This module turns that into questions by code, so a set is
ready at once, costs nothing, and takes the shape of the subject: a vocabulary becomes
matching and recall, a timeline becomes ordering, the lesson's checks come back as recall.

Nothing here asks a model, and nothing is taken from the lesson's closing quiz, so practising
never shows what the concept check is about to ask.
"""

import hashlib
import re

from socrat.catalog.registry import Catalog
from socrat.catalog.schema import Concept, Course, Section
from socrat.drills.service import QUESTIONS, Question

PROMPT_LIMIT = 600  # Question.prompt
SIDE_LIMIT = 80  # one side of a matching pair, so it fits a phone
MIN_SET = 3  # fewer bank items than this: the set is written by the model as before

# The kinds that suit a subject, most fitting first: the order a set is filled in, and what
# the model is asked to prefer when it writes a set. By studio, then by what the course has.
BY_STUDIO: dict[str, tuple[str, ...]] = {
    "code": ("choice", "order", "text"),
    "workbench": ("number", "choice", "order"),
    "lab": ("choice", "number", "order"),
    "reading": ("choice", "match", "order", "text"),
}
SECTION_KINDS = {"cards": "match", "table": "match", "timeline": "order", "list": "text"}
YOUNG = {"little-kid", "kid"}


def plan(course: Course, studio: str, register: str = "") -> list[str]:
    """Question kinds for this course, most fitting first. A course with sections practises
    them in their own shape first; a young learner gets tapping kinds before typing ones."""
    kinds = [SECTION_KINDS[s.style] for s in course.sections]
    kinds += list(BY_STUDIO.get(studio, BY_STUDIO["reading"]))
    if register in YOUNG:
        kinds = [k for k in kinds if k not in ("text", "number")] + ["text", "number"]
    return list(dict.fromkeys(kinds))


def _ref(*parts: str) -> str:
    """A stable id for one bank item, so what a learner has answered can be told apart."""
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:16]


def _question(ref: str, **fields) -> dict | None:
    try:
        return Question.model_validate(fields).model_dump() | {"ref": ref}
    except ValueError:
        return None  # not gradable as written: leave it out, keep the rest


def from_checks(cat: Catalog, qualified: str) -> list[dict]:
    """The lesson's own in-lesson checks as recall questions. Only checks that stand without
    code, and whose setup and question fit in one prompt."""
    pack = cat.atom_packs.get(qualified)
    if pack is None or pack.status != "released":
        return []
    out = []
    for atom in pack.atoms:
        if atom.adapters:
            continue  # reads a program the learner would not see here
        for index, step in enumerate(atom.steps):
            options = list(step.options)
            if step.answer >= len(options) or len(set(options)) != len(options):
                continue
            setup = step.state.strip()
            prompt = (
                step.prompt if not setup or setup in step.prompt else f"{setup}\n\n{step.prompt}"
            )
            if len(prompt) > PROMPT_LIMIT or not 2 <= len(options) <= 5:
                continue
            item = _question(
                _ref("check", qualified, atom.id, str(index)),
                kind="choice",
                prompt=prompt,
                options=options,
                answer=options[step.answer],
                explanation=step.explanation,
            )
            if item:
                out.append(item)
    return out


_YEAR = re.compile(r"^\s*(-?\d{1,4})\b")


def _rows(section: Section, concepts: list[Concept]) -> list[tuple[str, str, str]]:
    """(first field, second field, lesson title) of the section's entries, without repeats."""
    seen: set[str] = set()
    rows = []
    for concept in concepts:
        for entry in concept.entries:
            if entry.section != section.id or len(entry.values) < 2:
                continue
            left, right = entry.values[0].strip(), entry.values[1].strip()
            if left and right and left.lower() not in seen:
                seen.add(left.lower())
                rows.append((left, right, concept.title))
    return rows


def from_sections(course: Course, concept: Concept, earlier: list[Concept]) -> list[dict]:
    """Questions built from the course's own sections. This lesson's rows come first; rows of
    lessons the learner has finished fill a matching or ordering question up to size."""
    out: list[dict] = []
    for section in course.sections:
        if len(section.fields) < 2:
            continue
        first, second = section.fields[0].lower(), section.fields[1].lower()
        mine = _rows(section, [concept])
        if not mine:
            continue
        pool = mine + [r for r in _rows(section, earlier) if r[0] not in {m[0] for m in mine}]
        short = [r for r in pool if len(r[0]) <= SIDE_LIMIT and len(r[1]) <= SIDE_LIMIT]
        where = f"{course.id}:{concept.id}"
        dated = [(int(m.group(1)), r) for r in pool if (m := _YEAR.match(r[0]))]
        if section.style == "timeline" and len(dated) >= 3 and len(dated) == len(pool):
            ordered = [r for _, r in sorted(dated, key=lambda d: d[0])][:6]
            item = _question(
                _ref("order", where, section.id),
                kind="order",
                prompt=f"{section.title}: put these in order, earliest first.",
                sequence=[r[1][:SIDE_LIMIT] for r in ordered],
                explanation="; ".join(f"{r[0]}: {r[1]}" for r in ordered)[:800],
            )
            if item:
                out.append(item)
        elif len(short) >= 3:
            pairs = short[:5]
            item = _question(
                _ref("match", where, section.id),
                kind="match",
                prompt=f"{section.title}: match each {first} to its {second}.",
                pairs=[[r[0], r[1]] for r in pairs],
                explanation="; ".join(f"{r[0]} = {r[1]}" for r in pairs)[:800],
            )
            if item:
                out.append(item)
        for left, right, title in mine:
            if len(left.split()) > 3 or len(left) > 40 or len(right) > 300:
                continue  # a typed answer is a word or a short phrase
            item = _question(
                _ref("recall", where, section.id, left),
                kind="text",
                prompt=f"{section.title}. Which {first} is this? {right}",
                answer=left,
                explanation=f"{left}: {right} (from the lesson “{title}”).",
            )
            if item:
                out.append(item)
    return out


def pool(cat: Catalog, course: Course, qualified: str, earlier: list[Concept]) -> list[dict]:
    """Every bank question for one lesson."""
    concept = cat.concept(qualified)
    earlier = [c for c in earlier if c.id != concept.id]
    return from_sections(course, concept, earlier) + from_checks(cat, qualified)


def choose(items: list[dict], kinds: list[str], right: set[str], missed: set[str]) -> list[dict]:
    """A set from the pool: questions missed before first, then ones never answered, then
    the rest; within each, the kinds that suit the subject first, and never two questions of
    a kind in a row while another kind is waiting."""
    rank = {k: i for i, k in enumerate(kinds)}

    def group(item: dict) -> int:
        return 0 if item["ref"] in missed else 2 if item["ref"] in right else 1

    waiting = sorted(items, key=lambda q: (group(q), rank.get(q["kind"], len(rank))))
    chosen: list[dict] = []
    while waiting and len(chosen) < QUESTIONS:
        last = chosen[-1]["kind"] if chosen else ""
        tier = group(waiting[0])
        pick = next(
            (q for q in waiting if group(q) == tier and q["kind"] != last),
            waiting[0],
        )
        waiting.remove(pick)
        chosen.append(pick)
    return chosen


def history(records: list) -> tuple[set[str], set[str]]:
    """Bank items this learner got right, and ones they missed and have not got right since,
    from their stored practice sets (newest first)."""
    right: set[str] = set()
    missed: set[str] = set()
    for record in reversed(records):  # oldest first, so a later answer wins
        outcome = record.outcome
        for index, given in outcome.get("answers", {}).items():
            questions = outcome["questions"]
            ref = questions[int(index)].get("ref") if int(index) < len(questions) else None
            if not ref:
                continue
            if given["correct"]:
                right.add(ref)
                missed.discard(ref)
            else:
                missed.add(ref)
                right.discard(ref)
    return right, missed
