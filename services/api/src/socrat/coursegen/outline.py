"""Brief → outline: what the Course Architect is asked, what the Curriculum Critic checks,
and how an outline reply becomes a ``Course`` of planned concepts."""

import json

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from socrat.catalog.registry import Catalog
from socrat.catalog.schema import Course, Language, Ref, Slug


class Brief(BaseModel):
    """What the owner writes to start a course (about a page)."""

    model_config = ConfigDict(extra="forbid")
    id: Slug
    title: str = Field(min_length=2, max_length=80)
    audience: str = Field(min_length=10, max_length=600)
    outcome: str = Field(min_length=10, max_length=600)  # what learners can do at the end
    background: str = Field(default="", max_length=600)  # what learners already know
    languages: list[Language] = Field(default=["python"], min_length=1)
    reuse: list[Ref] = Field(default_factory=list, max_length=40)  # e.g. zero:loops
    references: list[str] = Field(default_factory=list, max_length=10)
    notes: str = Field(default="", max_length=2000)
    budget_usd: float = Field(default=5.0, gt=0, le=1000)
    # One concept package (all its rounds) may not cost more than this.
    concept_budget_usd: float = Field(default=2.0, gt=0, le=100)


def to_course(brief: Brief, outline: dict) -> Course:
    """Raises ValueError with a readable reason when the outline breaks the schema."""
    try:
        modules = outline["modules"]
        concepts = [
            {
                "id": c["id"],
                "title": c["title"],
                "summary": c["summary"],
                "module": m["id"],
                "prerequisites": c.get("prerequisites", []),
                "difficulty": c["difficulty"],
                "estimated_minutes": c["estimated_minutes"],
                "status": "planned",
                "outline": {
                    "depth": c.get("depth", "practitioner"),
                    "objectives": c["objectives"],
                    "misconceptions": c.get("misconceptions", []),
                    "assessment": c["assessment"],
                },
            }
            for m in modules
            for c in m["concepts"]
        ]
        payload = {
            "id": brief.id,
            "title": brief.title,
            "tagline": outline["tagline"],
            "description": outline["description"],
            "version": "0.1.0",
            "languages": brief.languages,
            "levels": outline["levels"],
            "modules": [
                {
                    "id": m["id"],
                    "title": m["title"],
                    "summary": m["summary"],
                    "concepts": [c["id"] for c in m["concepts"]],
                }
                for m in modules
            ],
            "concepts": concepts,
        }
    except (KeyError, TypeError) as exc:
        raise ValueError(f"outline is missing a required field: {exc}") from exc
    try:
        return Course.model_validate(payload)
    except ValidationError as exc:
        issues = [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()[:20]]
        raise ValueError("; ".join(issues)) from exc


def from_course(course: Course) -> dict:
    """The outline JSON shape again, for revisions and the critic."""
    by_id = {c.id: c for c in course.concepts}
    return {
        "tagline": course.tagline,
        "description": course.description,
        "levels": [level.model_dump(mode="json") for level in course.levels],
        "modules": [
            {
                "id": m.id,
                "title": m.title,
                "summary": m.summary,
                "concepts": [
                    {
                        "id": c.id,
                        "title": c.title,
                        "summary": c.summary,
                        "prerequisites": list(c.prerequisites),
                        "difficulty": c.difficulty,
                        "estimated_minutes": c.estimated_minutes,
                        **(c.outline.model_dump(mode="json") if c.outline else {}),
                    }
                    for c in (by_id[cid] for cid in m.concepts)
                ],
            }
            for m in course.modules
        ],
    }


def known_concepts(catalog: Catalog) -> str:
    """Existing concepts a new course may list as prerequisites, one per line."""
    return "\n".join(
        f"{key} — {catalog.concepts[key].title}"
        for course_id in catalog.courses
        for key in catalog.course_concepts(course_id)
    )


def gold_example(catalog: Catalog) -> str:
    """The hand-authored DSA course's shape: the granularity and ordering to match."""
    if "dsa" not in catalog.courses:
        return ""
    course = catalog.course("dsa")
    lines = []
    for m in course.modules:
        lines.append(f"Module {m.id}: {m.title} — {m.summary}")
        for cid in m.concepts:
            c = catalog.concept(f"dsa:{cid}")
            prereqs = ", ".join(c.prerequisites) or "none"
            lines.append(
                f"  - {cid} ({c.estimated_minutes} min, difficulty {c.difficulty}; "
                f"needs {prereqs}): {c.summary}"
            )
    return "\n".join(lines)


SHAPE = """{
  "tagline": "5-140 chars",
  "description": "20-1200 chars: what the course covers and who it is for",
  "levels": [
    {"id": "brand-new", "label": "...", "description": "...", "start_concept": null},
    {"id": "...", "label": "...", "description": "...", "start_concept": "<concept id in this course>"}
  ],
  "modules": [
    {"id": "kebab-case", "title": "...", "summary": "10-300 chars", "concepts": [
      {"id": "kebab-case, unique in the course",
       "title": "2-100 chars",
       "summary": "10-300 chars",
       "prerequisites": ["earlier-concept-id", "zero:existing-id"],
       "difficulty": 1-5,
       "estimated_minutes": 10-600,
       "depth": "overview | practitioner | mastery",
       "objectives": ["1-6 observable outcomes, each starting with a verb"],
       "misconceptions": ["up to 6 concrete wrong beliefs learners hold"],
       "assessment": ["quiz", "code", "explain", "project"]}
    ]}
  ]
}"""

ARCHITECT = f"""You are the Course Architect for Socrat, an adaptive learning platform whose
courses are deep enough to master a skill, not just survey it. You plan the whole outline
of a new course from the owner's brief. Other agents later write each concept's lesson
(worked examples, why it works, edge cases, self-checks), quizzes and exercises from your
outline, so every concept needs precise objectives.

Rules:
- A concept is too broad if a learner can be strong in one part and weak in another while
  needing the same next step. Split such concepts. A concept is roughly 20-90 minutes of
  focused study.
- Cover everything the outcome needs, from the learner's background up to mastery: plan
  as many concepts as that takes (a full skill course is usually 25-80 concepts in 4-12
  modules). Tag each concept's depth: "overview" if every learner needs it, "practitioner"
  for working competence, "mastery" for deep or advanced material.
- Prerequisites form a DAG. List only concepts that come earlier in this course, or
  existing Socrat concepts by their full id from the list given. Reuse an existing concept
  instead of re-teaching it. Modules are in learning order.
- Objectives are observable ("Compute...", "Explain why...", "Implement..."), never
  "understand". Misconceptions are specific wrong beliefs, not topics.
- Assessment: "quiz" always fits; "code" only when the course languages apply; "explain"
  for reasoning; "project" for module capstones.
- Levels: 2-4 self-reported starting points. The first has start_concept null.
- Write original text. Do not copy any published syllabus.

Reply with one JSON object only, in exactly this shape:
{SHAPE}"""

CRITIC = """You are the Curriculum Critic for Socrat. You review a course outline written by
another agent against the owner's brief, before any lesson is written. Be strict: fixing
the outline now is far cheaper than fixing lessons later.

Check:
- Coverage: can a learner with the stated background reach the outcome with these
  concepts alone? Name missing concepts.
- Granularity: concepts that bundle separable skills (split them), or trivial slivers
  (merge them).
- Order and prerequisites: missing or wrong edges, concepts used before they are taught,
  existing Socrat concepts that should be reused instead of re-taught.
- Depth tags fit the audience; objectives are observable; misconceptions are concrete.
- Duplicates, vague titles, levels whose start_concept makes no sense.

verdict is "pass" only when nothing blocking remains. Reply with one JSON object only:
{"verdict": "pass" | "revise",
 "summary": "2-3 sentences on the outline's quality",
 "issues": [{"where": "module or concept id", "problem": "...", "fix": "..."}]}"""


def architect_prompt(
    brief: Brief,
    catalog: Catalog,
    previous: dict | None = None,
    issues: list[str] | None = None,
) -> str:
    parts = [
        "Brief:\n" + brief.model_dump_json(indent=2, exclude={"budget_usd"}),
        "Existing Socrat concepts you may use as prerequisites:\n" + known_concepts(catalog),
        "For quality, granularity and ordering, match the hand-authored DSA course:\n"
        + gold_example(catalog),
    ]
    if previous is not None:
        parts.append("Your previous outline:\n" + json.dumps(previous, indent=1))
    if issues:
        parts.append(
            "Revise the outline to fix every issue below, keeping what already works. "
            "Reply with the complete revised outline.\n- " + "\n- ".join(issues)
        )
    return "\n\n".join(parts)


def critic_prompt(brief: Brief, outline: dict) -> str:
    return (
        "Brief:\n"
        + brief.model_dump_json(indent=2, exclude={"budget_usd"})
        + "\n\nOutline to review:\n"
        + json.dumps(outline, indent=1)
    )
