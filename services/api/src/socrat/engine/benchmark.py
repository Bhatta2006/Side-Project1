"""Course-generation benchmark (master prompt 16.1): representative requests and a deterministic
scorer for what the engine produced.

The scorer checks what code can check, per course: observable objectives, a sound prerequisite
graph, coherent module order, sources with provenance, assessment contracts, modalities the
subject's adapter allows, accessible visuals, and the cost and latency the jobs recorded. It is
a regression and triage tool. It does **not** judge factual correctness or teaching quality:
the prompt requires qualified human reviewers for a representative sample, and ``HUMAN_REVIEW``
lists what they must check. ``scripts/dev/benchmark.py`` runs the requests through the real
pipeline with a live model and writes a report.
"""

import re

from socrat.catalog.registry import Catalog
from socrat.catalog.schema import Course
from socrat.engine import assessments, domains, renderers

# The archetypes the prompts name (five from the first, eight subjects in all), phrased as a
# learner would.
REQUESTS = (
    ("children-math", "I am 8 and want to get good at fractions with games", "math-science"),
    (
        "university-physics",
        "Teach me quantum mechanics to graduate level, mathematics-heavy",
        "math-science",
    ),
    ("programming", "Prepare me for competitive programming interviews in Python", "software"),
    ("electrical", "Teach me electrical engineering through practical experiments", "electronics"),
    ("music", "Teach me Carnatic music and help me understand ragas", "music"),
    # Added for master prompt 2 (19.4). Language learning and workplace communication have no
    # dedicated adapter yet, so they run on the general one; the benchmark keeps that visible.
    (
        "language-speaking",
        "I want to become confident speaking English for job interviews, twenty minutes daily",
        "general",
    ),
    (
        "visual-creative",
        "I know Blender basics. Teach me animation and rigging through practical projects",
        "animation-movement",
    ),
    (
        "professional-communication",
        "Teach me business communication: writing clear emails and running meetings",
        "general",
    ),
)

HUMAN_REVIEW = (
    "Factual and mathematical correctness of every lesson and answer key",
    "Whether the prerequisites are the right ones for this audience",
    "Teaching quality: examples, pacing, misconceptions addressed",
    "Resource quality: authority, level fit, licence",
    "Fit for the stated age or register",
)

VERB = re.compile(
    r"^(apply|analy[sz]e|build|calculate|choose|classify|compare|compute|construct|convert|create|"
    r"debug|define|derive|describe|design|determine|distinguish|draw|estimate|evaluate|explain|"
    r"find|identify|implement|interpret|list|measure|model|name|perform|play|plot|predict|prove|"
    r"read|recognise|recognize|record|relate|represent|simplify|sing|sketch|solve|state|trace|"
    r"use|write)\b",
    re.I,
)


def _ratio(good: int, total: int) -> float | None:
    return round(good / total, 3) if total else None


def score(course: Course, catalog: Catalog, adapter_id: str, jobs: list | None = None) -> dict:
    """Deterministic metrics for one generated course (the merged catalog must contain it)."""
    adapter = domains.ADAPTERS.get(adapter_id, domains.ADAPTERS["general"])
    concepts = course.concepts
    objectives = [o for c in concepts if c.outline for o in c.outline.objectives]
    observable = sum(
        1 for o in objectives if VERB.match(o.strip()) and "understand" not in o.lower()
    )

    # Prerequisites point backwards in course order (or to existing courses): no forward edges.
    order = {cid: n for n, m in enumerate(course.modules) for cid in m.concepts}
    position = {cid: i for i, cid in enumerate(cid for m in course.modules for cid in m.concepts)}
    edges = forward = 0
    for c in concepts:
        for p in c.prerequisites:
            if ":" in p:
                continue
            edges += 1
            forward += position.get(p, -1) >= position.get(c.id, 0)
    # Coherence: modules never depend on a later module.
    backwards_modules = sum(
        1
        for c in concepts
        for p in c.prerequisites
        if ":" not in p and order.get(p, 0) > order.get(c.id, 0)
    )

    live = [c for c in concepts if c.status == "live"]
    cited = [r for c in live for r in c.resources]
    with_provenance = sum(1 for r in cited if r.license or r.source)
    contracts = [a for c in live for a in assessments.describe(c, f"{course.id}:{c.id}")]
    complete = sum(
        1
        for a in contracts
        if all(a[k] not in (None, "") for k in ("evaluation", "scoring", "evidence"))
    )
    visuals = [v for c in live for v in c.visuals]
    allowed = set(adapter.renderers)
    fitting = sum(
        1 for v in visuals if v.renderer in allowed and not renderers.validate_spec(v.model_dump())
    )
    accessible = sum(1 for v in visuals if v.alt_text and v.fallback_text)

    calls = [
        call
        for j in jobs or []
        for e in j.log or []
        if e.get("event") == "released"
        for call in e.get("calls", [])
    ]
    cost = round(sum(j.cost_usd for j in jobs or []), 4)
    return dict(
        course=course.id,
        adapter=adapter.id,
        concepts=len(concepts),
        released=len(live),
        objective_quality=_ratio(observable, len(objectives)),
        prerequisite_order=_ratio(edges - forward, edges) if edges else 1.0,
        module_coherence=1.0
        if backwards_modules == 0
        else round(1 - backwards_modules / max(1, len(concepts)), 3),
        resource_provenance=_ratio(with_provenance, len(cited)),
        assessment_contracts=_ratio(complete, len(contracts)),
        modality_fit=_ratio(fitting, len(visuals)),
        visual_accessibility=_ratio(accessible, len(visuals)),
        cost_usd=cost,
        model_calls=len(calls),
        model_ms=sum(int(c.get("ms", 0)) for c in calls),
        needs_human_review=list(HUMAN_REVIEW),
    )
