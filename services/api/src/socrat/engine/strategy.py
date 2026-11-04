"""The Pedagogical Strategist (master prompt 7.5 and 8.2): how to teach one concept to one learner.

Deterministic: rules over the concept's outline (category, difficulty, objectives, related
concepts, required evidence), the learner's stage (``mastery.evidence``) and the subject's domain
adapter. It may only choose techniques from the Learning Evidence Library and says why for each,
in words a learner can read. The lesson author is given the plan for a learner meeting the
concept for the first time (lessons are shared); the lesson page shows the plan for the learner's
own stage. No learning styles: preferences change wording and format, never the method.
"""

from dataclasses import dataclass, field

from socrat.engine import domains
from socrat.engine.evidence_library import BY_ID, VERSION

GUIDANCE = {
    "unknown": "high",
    "emerging": "high",
    "developing": "medium",
    "proficient": "low",
    "demonstrated": "low",
}
REPRESENTATION = {
    "math-science": "worked equations with a diagram or plot of the same idea",
    "software": "short runnable code next to its output, then the idea in words",
    "electronics": "a circuit diagram with values, then the simulation",
    "music": "notation and a description of the sound (audio needs a recording the learner makes)",
    "animation-movement": "a step-by-step timeline of poses or frames, then the learner's own attempt",
    "general": "plain text with one diagram where a structure or process is involved",
}


@dataclass
class Plan:
    stage: str
    guidance: str
    representation: str
    segment_minutes: int
    evidence: list[str]
    techniques: list[dict] = field(default_factory=list)  # {id, name, why}
    library: str = VERSION


def _pick(plan: Plan, technique: str, why: str) -> None:
    if technique not in BY_ID:
        raise ValueError(f"{technique} is not in the evidence library")
    if all(t["id"] != technique for t in plan.techniques):
        plan.techniques.append(dict(id=technique, name=BY_ID[technique].name, why=why))


def plan(concept, stage: str = "unknown", adapter: domains.Adapter | None = None) -> Plan:
    outline = concept.outline
    category = outline.category if outline else "knowledge"
    adapter = adapter or domains.ADAPTERS["general"]
    hard = concept.difficulty >= 4
    # Working memory: new and hard material in short segments, familiar material in longer ones.
    segment = (
        8
        if stage in ("unknown", "emerging") and hard
        else 12
        if stage in ("unknown", "emerging")
        else 20
    )
    evidence = (
        list(outline.evidence)
        if outline and outline.evidence
        else (
            ["application", "explanation"] if category != "knowledge" else ["recall", "explanation"]
        )
    )
    out = Plan(
        stage=stage,
        guidance=GUIDANCE.get(stage, "high"),
        representation=REPRESENTATION.get(adapter.id, REPRESENTATION["general"]),
        segment_minutes=min(segment, concept.estimated_minutes),
        evidence=evidence,
    )
    _pick(out, "feedback", "Every answer is checked and explained, so mistakes are fixed early.")
    if stage in ("unknown", "emerging"):
        _pick(
            out,
            "worked-examples",
            "It is new to you, so you see a full worked example before trying one.",
        )
        _pick(out, "scaffolding", "Hints start small and grow only if you need them.")
        if hard or category == "knowledge":
            _pick(out, "concreteness-fading", "A concrete example comes before the general rule.")
        if adapter.renderers and any(r != "markdown" for r in adapter.renderers):
            _pick(out, "dual-coding", "A picture shows the same idea as the words, when it helps.")
        _pick(
            out,
            "retrieval",
            "After reading, a few questions ask you to recall it, which makes it stick.",
        )
    elif stage == "developing":
        _pick(out, "retrieval", "You recall it before seeing answers, which strengthens memory.")
        _pick(out, "spacing", "Reviews come back after growing gaps, so it lasts.")
        _pick(out, "self-explanation", "You explain why a step works, not just what it is.")
        if outline and outline.related:
            _pick(
                out, "interleaving", "Mixed practice with related ideas helps you tell them apart."
            )
    else:
        _pick(out, "spacing", "You know it; spaced reviews keep it from fading.")
        _pick(out, "cumulative-review", "Earlier ideas come back while you learn new ones.")
        if stage == "proficient":
            _pick(out, "transfer", "Next you use it on something new, to show it carries over.")
            _pick(out, "desirable-difficulty", "Practice gets harder because you are succeeding.")
    if category in ("skill", "both") or adapter.needs_physical_practice:
        _pick(
            out,
            "deliberate-practice",
            "Practice targets the part you get wrong most, with clear criteria.",
        )
    if stage != "unknown":
        _pick(
            out,
            "calibration",
            "You can say how sure you are, and see how that compares with how you did.",
        )
    return out


def brief(p: Plan) -> str:
    """The plan as instructions for the lesson author."""
    lines = [
        f"Teaching plan (Socrat evidence library {p.library}) for a learner meeting this concept "
        f"for the first time: guidance {p.guidance}; represent it as {p.representation}; keep "
        f"each segment to about {p.segment_minutes} minutes of reading or doing; the concept is "
        f"learned when the learner shows {', '.join(p.evidence)}.",
        "Techniques to use:",
        *[f"- {t['name']}: {BY_ID[t['id']].rule}" for t in p.techniques],
        "Do not label the learner (no learning styles); preferences only change wording and format.",
    ]
    return "\n".join(lines)
