"""An "Apply" lesson at the end of every module of a learner's course.

Wondering ends each section with an applied lesson ("Apply the key ideas from <section> in a
practical scenario before the section review"; research/wondering/2026-11-05, rows with
``isAppliedLesson``). Lessons one idea at a time leave a gap: the learner never has to choose
which idea fits, or use two together. This adds that step to Socrat's outline, built by code (no
model decides the plan): one planned concept per module of two or more concepts, placed after
the module's last concept, depending on the module's concepts that nothing else in the module
builds on, so it opens once the module is done. Its contract asks for use of the module's ideas
together in a situation the lessons did not show, checked by a quiz and a free-text answer
graded against a rubric. The package job writes it like any other planned concept.

What it does not do: transfer checks in Socrat are judged problems (``learn/transfers.py``), so
this lesson's own quiz and explanation are its evidence; it does not add transfer evidence to
the module's earlier concepts.
"""

from socrat.catalog.schema import Concept, Course

PREFIX = "apply-"
MAX_PREREQUISITES = 4
MAX_MINUTES = 30


def _id(module_id: str, taken: set[str]) -> str:
    local = f"{PREFIX}{module_id}"[:64].rstrip("-")
    return local if local not in taken else ""


def is_applied(concept_id: str) -> bool:
    return concept_id.startswith(PREFIX)


def lesson(course: Course, module_id: str, taken: set[str]) -> Concept | None:
    """The applied concept for one module, or None when the module has nothing to combine or
    already has one."""
    module = next((m for m in course.modules if m.id == module_id), None)
    if module is None:
        return None
    members = [course.concept(cid) for cid in module.concepts if not is_applied(cid)]
    if len(members) < 2 or any(is_applied(cid) for cid in module.concepts):
        return None
    local = _id(module.id, taken)
    if not local:
        return None
    inside = {c.id for c in members}
    built_on = {p for c in members for p in c.prerequisites if p in inside}
    leaves = [c.id for c in members if c.id not in built_on] or [members[-1].id]
    names = [c.title for c in members]
    listed = ", ".join(names[:-1]) + f" and {names[-1]}" if len(names) > 1 else names[0]
    misconceptions = [m for c in members if c.outline for m in c.outline.misconceptions]
    depth = next((c.outline.depth for c in members if c.outline), "practitioner")
    return Concept.model_validate(
        {
            "id": local,
            "title": f"Apply: {module.title}"[:100],
            "summary": f"Use {listed} together in a situation the lessons did not show."[:300],
            "module": module.id,
            "prerequisites": leaves[-MAX_PREREQUISITES:],
            "difficulty": max(c.difficulty for c in members),
            "estimated_minutes": min(MAX_MINUTES, max(c.estimated_minutes for c in members)),
            "status": "planned",
            "outline": {
                "depth": depth,
                "objectives": [
                    f"Choose which idea from {module.title} fits a new situation"[:200],
                    f"Combine {listed} to solve one realistic problem"[:200],
                    "Explain why the chosen approach works in that situation",
                ],
                "misconceptions": list(dict.fromkeys(misconceptions))[:3],
                "assessment": ["quiz", "explain"],
                "category": "both",
                "evidence": ["application", "transfer", "explanation"],
                "expected": (
                    f"Solves an unseen {module.title} problem by picking and combining the "
                    "right ideas, and says why."
                )[:300],
                "practice": ["problem-set", "worked-example"],
            },
        }
    )


def remove(course: Course) -> Course:
    """``course`` without its applied lessons (the architect's plan as it was). Raises
    ValueError if another concept was made to depend on one."""
    gone = {c.id for c in course.concepts if is_applied(c.id)}
    if not gone:
        return course
    return Course.model_validate(
        {
            **course.model_dump(mode="json"),
            "concepts": [c.model_dump(mode="json") for c in course.concepts if c.id not in gone],
            "modules": [
                m.model_dump(mode="json")
                | {"concepts": [cid for cid in m.concepts if cid not in gone]}
                for m in course.modules
            ],
        }
    )


def add(course: Course) -> Course:
    """``course`` with an applied lesson closing each module that has two or more concepts.
    Idempotent: a module that already ends with one is left as it is."""
    taken = {c.id for c in course.concepts}
    made: dict[str, Concept] = {}
    for module in course.modules:
        concept = lesson(course, module.id, taken)
        if concept is not None:
            made[module.id] = concept
            taken.add(concept.id)
    if not made:
        return course
    last = {m.id: m.concepts[-1] for m in course.modules if m.id in made}
    concepts: list[Concept] = []
    for c in course.concepts:
        concepts.append(c)
        if c.module in made and c.id == last[c.module]:
            concepts.append(made[c.module])
    modules = [
        m.model_copy(update={"concepts": [*m.concepts, made[m.id].id]}) if m.id in made else m
        for m in course.modules
    ]
    # Round-trip so the course's own validation (references, order) runs on the result.
    return Course.model_validate(
        {
            **course.model_dump(mode="json"),
            "concepts": [c.model_dump(mode="json") for c in concepts],
            "modules": [m.model_dump(mode="json") for m in modules],
        }
    )
