"""Brief → outline: what the Course Architect is asked, what the Curriculum Critic checks,
and how an outline reply becomes a ``Course`` of planned concepts."""

import json
from typing import get_args

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from socrat.catalog import shape
from socrat.catalog.registry import Catalog
from socrat.catalog.schema import Course, EvidenceType, Language, PracticeType, Ref, Slug
from socrat.style import pages
from socrat.style import spec as styles


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
    # How learners want to learn (admin testing): a ready style, or a free-text wish the
    # Stylist agent turns into one before the outline is written.
    style: styles.StyleSpec | None = None
    style_request: str = Field(default="", max_length=600)
    # The learner's stated session length (fixed choice); it decides lesson size, see
    # ``styles.for_session``. None: not stated.
    session_minutes: int | None = Field(default=None, ge=1, le=480)
    # The learner's own notes the course is built from (untrusted data). Never part of the
    # brief JSON in prompts; ``brief_text`` adds it as its own marked block.
    material: str = Field(default="", max_length=20000)
    budget_usd: float = Field(default=5.0, gt=0, le=1000)
    # One concept package (all its rounds) may not cost more than this.
    concept_budget_usd: float = Field(default=2.0, gt=0, le=100)
    # A researcher finds public sources first; lessons cite them and credit them.
    research: bool = True
    # The domain adapter the intent parser chose (engine.domains); empty = classify the title.
    adapter: str = Field(default="", max_length=40)
    # Safety notes from the request; a lesson in such a course needs a person to confirm it.
    safety: list[str] = Field(default_factory=list, max_length=10)
    # Who reads the course, from the learner's request (style/pages.py sizes lesson pages from
    # it). None for admin briefs: the style alone decides.
    learner: pages.Learner | None = None


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
                    **{
                        k: c[k]
                        for k in ("category", "related", "evidence", "expected", "practice")
                        if k in c
                    },
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
            "shape": outline["shape"],
            "sections": outline.get("sections") or [],
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
        "shape": shape.effective(course).model_dump(mode="json"),
        "sections": [s.model_dump(mode="json") for s in course.sections],
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


# Adapters whose courses are programming courses ("" is a course made before adapters existed).
SOFTWARE_ADAPTERS = {"", "software"}
# What the DSA example teaches the architect, said without the DSA: for every other subject.
GRANULARITY = """Granularity and ordering: this course stands alone, so every prerequisite is a
concept of this course. One concept is one idea a learner can study in a single sitting of the
length they asked for; split anything bigger. Order concepts so each uses only what came before,
group them into modules of 3 to 7 that each end in something the learner can do, and let the
subject decide the shape: do not borrow the structure of a programming course."""


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
  "shape": {
    "studio": "code | workbench | lab | reading",
    "loop": "solve | derive | predict-observe-explain | read-reflect",
    "evidence": ["tests | derivation | numeric | explanation | quiz (1-4, distinct)"],
    "tools": ["editor | graph | cas | simulation (0-3, distinct)"],
    "label": "optional name for the practice area, at most 24 chars"
  },
  "sections": [
    {"id": "kebab-case", "title": "2-40 chars, what the learner sees",
     "purpose": "10-200 chars: what it collects and why this subject needs it",
     "style": "cards | table | timeline | list",
     "fields": ["1-4 short names for what one entry holds, in order"]}
  ],
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
       "estimated_minutes": 10-600 (3-600 when the learning style asks for short sessions),
       "depth": "overview | practitioner | mastery"}
    ]}
  ],
  "assumptions": ["what you assumed about the learner or subject that the brief did not say"],
  "unresolved": ["prerequisite questions you could not settle; empty when none"]
}"""

# What each concept gets once the skeleton stands, written per module in parallel.
DETAIL_FIELDS = (
    "objectives",
    "misconceptions",
    "assessment",
    "category",
    "related",
    "evidence",
    "expected",
    "practice",
)

DETAIL_SHAPE = """{"concepts": [
  {"id": "the concept id, exactly as given",
   "objectives": ["1-6 observable outcomes, each starting with a verb"],
   "misconceptions": ["up to 6 concrete wrong beliefs learners hold"],
   "assessment": ["quiz", "code", "explain", "project"],
   "category": "knowledge | skill | both",
   "related": ["concept ids that connect without being required first (0-6)"],
   "evidence": ["recognition | recall | application | transfer | explanation | performance"],
   "expected": "at most 300 chars: the observable performance that shows the concept is learned",
   "practice": ["retrieval | worked-example | problem-set | lab | project | performance | reflection | discussion"]}
]}"""

ARCHITECT = f"""You are the Course Architect for Socrat, an adaptive learning platform whose
courses are deep enough to master a skill, not just survey it. You plan the whole outline
of a new course from the owner's brief: its modules and concepts, their order and their
prerequisites. Each concept's objectives, misconceptions and evidence are written next, one
module at a time, from your plan, so make every title and summary precise.

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
- List your assumptions about the learner and any prerequisite questions you could not settle,
  so the learner and the critic can see them. Do not hide uncertainty.
- Levels: 2-4 self-reported starting points. The first has start_concept null.
- Shape: how this subject is practised and proven. Choose the studio from what learners
  actually do. code: programming (editor, tests). workbench: math (graphs, symbolic
  answers, derivations; loop solve or derive). lab: physics or science with simulations
  (loop predict-observe-explain). reading: any other subject until it has its own studio
  (quiz and explanation only). Pick only evidence and tools that studio supports. A course
  with no code should not list the editor tool or the tests evidence.
- Sections: 0-4 parts of its own this subject needs beyond lessons and practice, which
  fill up entry by entry as lessons are written. A language course needs a vocabulary
  (fields: word, meaning, example); history a timeline (date, event, why it matters);
  music a repertoire; law a list of cases; chemistry a table of reactions; a children's
  course a sticker book of things discovered. Add a section only when a learner of this
  subject would really go back to it; none is right for many courses. Do not add sections
  for key points, common mistakes, formulas or sources: every course has those already.
- Write original text. Do not copy any published syllabus.
- If the brief carries a learning style, it governs the plan: concept size follows the
  session length (a 5-minute session means 3-8 minute concepts and many of them), depth tags
  follow the learner and rigor, and titles speak the learner's register.

Reply with one JSON object only, in exactly this shape:
{SHAPE}"""

DETAILER = f"""You are the Course Architect for Socrat. The course outline is planned; you now
write the details of a few concepts of one module so other agents can write each lesson
(worked examples, why it works, edge cases, self-checks), quizzes and exercises from them.

Rules:
- Objectives are observable ("Compute...", "Explain why...", "Implement..."), never
  "understand". Misconceptions are specific wrong beliefs, not topics.
- Assessment: "quiz" always fits; "code" only when the course languages apply; "explain"
  for reasoning; "project" for module capstones.
- The outline is a competency graph, not a list. For each concept say whether it is
  knowledge, a skill, or both; which other concepts of the course it relates to without
  needing them first (never one of its prerequisites, never itself); what evidence shows it is
  learned (recognising a right answer is weaker than recalling it, applying it, transferring it
  to an unfamiliar case, explaining it, or performing it); the observable performance expected;
  and the practice that builds it. A skill needs application or performance evidence, not only
  recognition. A subject learned by doing (music, movement, hands-on electronics) needs
  performance evidence and says that a person must judge it.
- If the brief carries a learning style, assessments follow the learner and rigor (no "code"
  or "project" for young learners or overviews unless asked).
- Write every concept you are given, by its exact id, and no others.

Reply with one JSON object only, in exactly this shape:
{DETAIL_SHAPE}"""

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
- Depth tags fit the audience. When concepts carry objectives and misconceptions, objectives
  are observable and misconceptions concrete; an outline without them is a plan whose details
  are written separately, so their absence is not an issue.
- Style fit: when the brief has a learning style, concept size, depth, assessments and
  titles must suit it (a mismatch is blocking).
- Duplicates, vague titles, levels whose start_concept makes no sense.
- Shape: the studio, loop and evidence must fit how this subject is really learned (a
  physics course on the code studio, or a math course proven by tests, is blocking). The
  studios are fixed: code, workbench, lab and reading, with only the loops, evidence and tools
  in the outline's shape. "reading" is the right studio for every subject without its own
  (drawing, music, finance, languages, ...); never ask for another studio, loop or evidence
  type, and never treat reading for such a subject as an issue.

List blocking issues only, at most 10, each in a sentence or two; skip praise and nitpicks.
verdict is "pass" only when nothing blocking remains. Reply with one JSON object only:
{"verdict": "pass" | "revise",
 "summary": "2-3 sentences on the outline's quality",
 "issues": [{"where": "module or concept id", "problem": "...", "fix": "..."}]}"""


def brief_text(brief: Brief) -> str:
    """The brief for the architect and critic: JSON of its settings, then the learner's own
    material (if any) as a separate block marked as data."""
    from socrat.coursegen.intent import material_block

    # The learner profile sizes lesson pages; the architect already reads the same facts in
    # the audience and notes, so it is left out rather than said twice.
    head = "Brief:\n" + brief.model_dump_json(
        indent=2, exclude={"budget_usd", "material", "learner"}
    )
    notes = material_block(brief.material, 12000) if brief.material.strip() else ""
    return f"{head}\n\nBuild the course around this material:\n{notes}" if notes else head


def architect_prompt(
    brief: Brief,
    catalog: Catalog,
    previous: dict | None = None,
    issues: list[str] | None = None,
) -> str:
    parts = [brief_text(brief), *([styles.block(brief.style)] if brief.style else [])]
    if brief.adapter in SOFTWARE_ADAPTERS:
        # Only a programming course can build on the hand-authored programming courses, and only
        # it is helped by their shape. Every other subject used to get both (hundreds of lines of
        # DSA in a children's physics prompt): slower, dearer and pulling the plan towards code.
        parts += [
            "Existing Socrat concepts you may use as prerequisites:\n" + known_concepts(catalog),
            "For quality, granularity and ordering, match the hand-authored DSA course:\n"
            + gold_example(catalog),
        ]
    else:
        parts.append(GRANULARITY)
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
        brief_text(brief)
        + (f"\n\n{styles.block(brief.style)}" if brief.style else "")
        + "\n\nOutline to review:\n"
        + json.dumps(outline, indent=1)
    )


def needs_detail(outline: dict) -> bool:
    """True when the architect planned the skeleton only (the usual case); an outline that
    already carries every concept's objectives and assessment is used as it is."""
    concepts = [c for m in outline.get("modules", []) for c in m.get("concepts", [])]
    return any(not (c.get("objectives") and c.get("assessment")) for c in concepts)


def skeleton_of(outline: dict) -> dict:
    """The outline without per-concept details: what the architect revises, kept short."""
    return {
        **outline,
        "modules": [
            {
                **m,
                "concepts": [
                    {k: v for k, v in c.items() if k not in DETAIL_FIELDS}
                    for c in m.get("concepts", [])
                ],
            }
            for m in outline.get("modules", [])
        ],
    }


def detail_prompt(
    brief: Brief,
    skeleton: dict,
    module_id: str,
    concept_ids: list[str],
    issues: list[str] | None = None,
) -> str:
    plan = "\n".join(
        f"- {m.get('id')}: {m.get('title', '')}\n"
        + "\n".join(
            f"  - {c.get('id')}: {c.get('title', '')}"
            f" (needs: {', '.join(map(str, c.get('prerequisites', []))) or 'none'})"
            for c in m.get("concepts", [])
            if isinstance(c, dict)
        )
        for m in skeleton.get("modules", [])
        if isinstance(m, dict)
    )
    module = next(m for m in skeleton["modules"] if m.get("id") == module_id)
    wanted = [c for c in module["concepts"] if c.get("id") in concept_ids]
    parts = [
        brief_text(brief),
        *([styles.block(brief.style)] if brief.style else []),
        "Studio and evidence of the course:\n" + json.dumps(skeleton.get("shape", {})),
        "The whole course plan, for related concepts:\n" + plan,
        f"Module {module_id}: {module.get('title', '')} ({module.get('summary', '')})",
        "Write the details of these concepts:\n" + json.dumps(wanted, indent=1),
    ]
    if issues:
        parts.append(
            "A reviewer raised these issues; fix any that concern these concepts:\n- "
            + "\n- ".join(issues)
        )
    return "\n\n".join(parts)


def merge_details(skeleton: dict, concept_ids: list[str], reply: dict) -> list[str]:
    """Copies the details of ``concept_ids`` into the skeleton; returns the ids still missing."""
    given = {
        c["id"]: c
        for c in reply.get("concepts", [])
        if isinstance(c, dict) and isinstance(c.get("id"), str)
    }
    wanted = set(concept_ids)
    missing = []
    for m in skeleton["modules"]:
        for c in m["concepts"]:
            if c["id"] not in wanted:
                continue
            detail = given.get(c["id"])
            if not detail or not detail.get("objectives") or not detail.get("assessment"):
                missing.append(c["id"])
                continue
            c.update({k: detail[k] for k in DETAIL_FIELDS if k in detail})
    return missing


_ASSESSMENT = ("quiz", "code", "explain", "project")
_LISTS = {  # field -> (allowed values or None for free text, most kept)
    "assessment": (_ASSESSMENT, 4),
    "evidence": (get_args(EvidenceType), 5),
    "practice": (get_args(PracticeType), 5),
    "objectives": (None, 6),
    "misconceptions": (None, 6),
}
_CHOICES = {
    "category": ("knowledge", "skill", "both"),
    "depth": ("overview", "practitioner", "mastery"),
}


def _clip(text: str, limit: int) -> str:
    """Cut at the last word that fits, so an over-long sentence still reads as one."""
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:")
    return cut + "…"


_LOOP_FIRST = ("solve", "predict-observe-explain", "read-reflect", "derive")


# Studios a subject may use, by the intent's adapter (engine.domains), first is the default.
# A live run gave a cooking course the physics lab: its quiz then had to be simulator
# experiments, which failed every round and cost the most. Adapters not listed (general, music,
# animation-movement) have no studio of their own yet.
STUDIOS_FOR = {
    "software": ("code", "reading"),
    "math-science": ("workbench", "lab", "reading"),
    "electronics": ("lab", "reading"),
}


def _tidy_shape(given: dict, adapter: str = "") -> None:
    """Keeps only what the chosen studio supports. An unknown studio becomes "reading", the
    studio the architect is told to use for any subject without its own; with an ``adapter``
    the studio must also suit the subject."""
    if given.get("studio") not in shape.STUDIOS:
        given["studio"] = "reading"
    label = given.get("label")
    if isinstance(label, str) and len(label) > 24:  # cost two whole architect rounds live
        given["label"] = label[:24].rsplit(" ", 1)[0].strip() if " " in label[:24] else label[:24]
    if adapter:
        fits = STUDIOS_FOR.get(adapter, ("reading",))
        if given["studio"] not in fits:
            given["studio"] = fits[0]
    allowed = shape.STUDIOS[given["studio"]]
    if given.get("loop") not in allowed["loops"]:
        given["loop"] = next(loop for loop in _LOOP_FIRST if loop in allowed["loops"])
    for name, most, fallback in (("evidence", 4, ["quiz"]), ("tools", 3, [])):
        raw = given.get(name)
        values = raw if isinstance(raw, list) else []
        kept = list(dict.fromkeys(v for v in values if v in allowed[name]))[:most]
        given[name] = kept or fallback


# Every course has these built from its lessons (learn/sections.py); a planned section
# with one of these ids or names would only repeat them.
BUILT_IN_SECTIONS = {"key-ideas", "mistakes", "formulas", "sources"}
SECTION_STYLES = {"cards", "table", "timeline", "list"}


def tidy_sections(given) -> list[dict]:
    """The course's own sections, repaired or dropped by code: a section is an extra, so a
    malformed one is left out instead of failing the outline. At most four, ids distinct."""
    from socrat.catalog.schema import Section

    kept: list[dict] = []
    for raw in given if isinstance(given, list) else []:
        if not isinstance(raw, dict):
            continue
        named = raw.get("fields")
        fields = [
            str(f).strip()[:24]
            for f in (named if isinstance(named, list) else [])
            if str(f).strip()
        ][:4]
        section = {
            "id": str(raw.get("id", "")).strip().lower(),
            "title": str(raw.get("title", "")).strip()[:40],
            "purpose": str(raw.get("purpose", "")).strip()[:200],
            "style": raw.get("style") if raw.get("style") in SECTION_STYLES else "list",
            "fields": fields,
        }
        try:
            Section.model_validate(section)
        except ValueError:
            continue
        if section["id"] in BUILT_IN_SECTIONS or section["id"] in {s["id"] for s in kept}:
            continue
        kept.append(section)
    return kept[:4]


def tidy(outline: dict, catalog: Catalog, adapter: str = "") -> dict:
    """Deterministic repairs of slips that need no model, instead of a whole new round:
    - a concept related to itself, to one of its own prerequisites, or to a concept that does
      not exist (related links are optional context, so dropping one never changes what is
      taught);
    - list values outside the allowed set, duplicates and lists over their limit;
    - an unknown category or depth (the schema default applies);
    - an expected performance over 300 characters (cut at a word).
    An empty assessment becomes ["quiz"], which fits every concept."""
    concepts = [
        c
        for m in outline.get("modules", [])
        if isinstance(m, dict) and isinstance(m.get("concepts"), list)
        for c in m["concepts"]
        if isinstance(c, dict)
    ]
    if isinstance(outline.get("shape"), dict):
        _tidy_shape(outline["shape"], adapter)
    outline["sections"] = tidy_sections(outline.get("sections"))
    # A planned activity the course's studio cannot produce is dropped here, before any lesson
    # is written against it (see ``shape.NEEDS_STUDIO``). No shape yet means a code course.
    studio = outline["shape"]["studio"] if isinstance(outline.get("shape"), dict) else "code"
    ids = {c.get("id") for c in concepts}
    for c in concepts:
        related = c.get("related")
        if isinstance(related, list):
            needs = set(c.get("prerequisites") or [])
            c["related"] = [
                r
                for r in dict.fromkeys(x for x in related if isinstance(x, str))
                if r != c.get("id") and r not in needs and (r in ids or r in catalog.concepts)
            ][:6]
        for name, (allowed, most) in _LISTS.items():
            values = c.get(name)
            if not isinstance(values, list):
                continue
            kept = [v for v in values if isinstance(v, str) and v.strip()]
            if allowed is not None:
                kept = [v for v in kept if v in allowed]
            if name in ("assessment", "practice"):
                kept = shape.producible(studio, name, kept)
            c[name] = list(dict.fromkeys(kept))[:most]
        if "assessment" in c and not c["assessment"]:
            c["assessment"] = ["quiz"]
        for name, allowed in _CHOICES.items():
            if name in c and c[name] not in allowed:
                del c[name]
        if isinstance(c.get("expected"), str):
            c["expected"] = _clip(c["expected"], 300)
    return outline


def graph_issues(course: Course, adapter=None) -> list[str]:
    """Problems with the competency graph that code can see. Fields the architect left empty are
    not judged (older outlines have none); what it did fill in must be consistent."""
    issues = []
    for c in course.concepts:
        o = c.outline
        if o is None:
            continue
        if o.category in ("skill", "both") and o.evidence and set(o.evidence) <= {"recognition"}:
            issues.append(
                f"{c.id}: a {o.category} concept needs application or performance evidence, "
                "not only recognition."
            )
        if c.id in o.related:
            issues.append(f"{c.id}: a concept cannot be related to itself.")
        if overlap := sorted(set(o.related) & set(c.prerequisites)):
            issues.append(f"{c.id}: {', '.join(overlap)} is already a prerequisite, not related.")
    filled = [c.outline for c in course.concepts if c.outline and c.outline.evidence]
    if adapter is not None and adapter.needs_physical_practice and filled:
        if not any("performance" in o.evidence for o in filled):
            issues.append(
                f"{adapter.name} is learned by doing: at least one concept needs performance "
                "evidence judged by a person."
            )
    return issues
