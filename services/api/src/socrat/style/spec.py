"""How someone wants to learn, as data every part of the engine can read.

A ``StyleSpec`` is the one contract between a free-text wish ("quantum mechanics for kids
under 10", "Harvard-level math", "5 minutes of physics a day") and the agents that build and
teach: the course architect sizes concepts by it, the authors shape lessons by it, the
gates and reviewer hold them to it, and the tutor speaks it. Presets cover common styles;
the Stylist agent (``interpret``) turns anything else into the same shape.
"""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

STYLE_KEY = "learning_style"  # in Enrollment.adaptive (path style lives under "style")

Depth = Literal["overview", "practitioner", "mastery"]
Format = Literal["bite", "standard", "deep"]
Tone = Literal["warm", "playful", "formal", "neutral"]
Tutor = Literal["socratic", "coach", "direct"]
Rigor = Literal["intuitive", "standard", "rigorous"]

# Lesson length floors in characters, by depth, for the standard format.
LESSON_FLOOR = {"overview": 2000, "practitioner": 3000, "mastery": 4000}
BITE_RANGE = (500, 1800)
BITE_MINUTES = 10  # a stated session this short gets bite-sized lessons (as the presets do)
DEEP_EXTRA = 1000


def for_session(spec: "StyleSpec | None", minutes: int | None) -> "StyleSpec | None":
    """The course style fitted to the learner's stated session length. Before this, "5
    minutes a day" was only a sentence to the writer while the gate still asked for a
    2,000-4,000 character lesson, so lessons failed for being as short as asked."""
    if not minutes:
        return spec
    if spec is None and minutes > BITE_MINUTES:
        return None  # a standard lesson fits; no style, so nothing else changes
    return (spec or StyleSpec(name=f"{minutes} minutes a session")).fitted(minutes)


class StyleSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(default="Custom", min_length=2, max_length=60)
    learner: str = Field(default="", max_length=200)  # who: "children under 10"
    level: str = Field(default="", max_length=120)  # "Harvard-level undergraduate"
    depth: Depth = "practitioner"
    format: Format = "standard"  # bite: one small idea per sitting; deep: long and thorough
    session_minutes: int = Field(default=30, ge=3, le=120)
    tone: Tone = "warm"
    tutor: Tutor = (
        "socratic"  # coach: guides with encouragement and examples; direct: answers first
    )
    rigor: Rigor = "standard"  # intuitive: no formalism; rigorous: derivations and proofs
    gamified: bool = False
    notes: str = Field(default="", max_length=600)  # the learner's own words, kept verbatim

    def lesson_bounds(self) -> tuple[int, int | None]:
        floor = LESSON_FLOOR[self.depth]
        if self.format == "bite":
            return BITE_RANGE
        if self.format == "deep":
            return floor + DEEP_EXTRA, None
        return floor, None

    def fitted(self, minutes: int | None) -> "StyleSpec":
        """This style for a learner who said how long a session is. 10 minutes or less is a
        bite-sized lesson (one idea per sitting) unless the learner asked for deep lessons;
        the session length is theirs either way."""
        if not minutes:
            return self
        update: dict = {"session_minutes": max(3, min(minutes, 120))}
        if minutes <= BITE_MINUTES and self.format == "standard":
            update["format"] = "bite"
        return self.model_copy(update=update)

    def min_headings(self) -> int:
        return 1 if self.format == "bite" else 3

    def shows_reference(self) -> bool:
        """The hand-authored reference lesson is a model for long, plain lessons only."""
        return self.format != "bite" and not self.gamified and self.tone != "playful"


PRESETS: dict[str, StyleSpec] = {
    "standard": StyleSpec(name="Standard"),
    "gamified": StyleSpec(
        name="Gamified",
        tone="playful",
        tutor="coach",
        gamified=True,
        notes="Quests, levels and streaks; every step feels like progress.",
    ),
    "in-depth": StyleSpec(
        name="In depth",
        depth="mastery",
        format="deep",
        session_minutes=60,
        rigor="rigorous",
        tone="formal",
        notes="Thorough: derivations, edge cases and the reasons behind every rule.",
    ),
    "overview": StyleSpec(
        name="Top-level overview",
        depth="overview",
        format="bite",
        session_minutes=10,
        rigor="intuitive",
        tutor="direct",
        notes="The big picture and key terms; skip derivations and detail.",
    ),
    "kids": StyleSpec(
        name="For kids",
        learner="children under 10",
        level="primary school; no prior knowledge",
        depth="overview",
        format="bite",
        session_minutes=10,
        tone="playful",
        tutor="coach",
        rigor="intuitive",
        gamified=True,
        notes="Short words, everyday analogies, stories and games; no jargon or formulas.",
    ),
    "daily-5": StyleSpec(
        name="Daily 5 minutes",
        depth="overview",
        format="bite",
        session_minutes=5,
        rigor="intuitive",
        tutor="direct",
        notes="One small idea a day that fits in five minutes.",
    ),
    "rigorous": StyleSpec(
        name="University level",
        learner="a motivated university student",
        level="Harvard-level undergraduate",
        depth="mastery",
        format="deep",
        session_minutes=60,
        rigor="rigorous",
        tone="formal",
        notes="Precise definitions, proofs or derivations, and hard problems.",
    ),
}

# Wording a request may use -> the preset to start from (first match wins).
_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(kids?|child(ren)?|under\s*1\d|age[sd]?\s*\d|toddler)\b", re.I), "kids"),
    (re.compile(r"\b(5|five)[\s-]*min", re.I), "daily-5"),
    (
        re.compile(r"\b(harvard|mit|olympiad|rigorous|proof|university|graduate)\b", re.I),
        "rigorous",
    ),
    (re.compile(r"\b(gamif\w*|game|quest|fun|playful)\b", re.I), "gamified"),
    (re.compile(r"\b(in[\s-]?depth|deep|thorough|comprehensive)\b", re.I), "in-depth"),
    (re.compile(r"\b(overview|top[\s-]?level|big picture|summary|quick)\b", re.I), "overview"),
]


def from_rules(request: str) -> StyleSpec:
    """A preset chosen by keywords, carrying the request as notes. The fallback when no
    model is available, and the answer for the simplest wishes."""
    text = request.strip()
    for pattern, key in _RULES:
        if pattern.search(text):
            return PRESETS[key].model_copy(update={"notes": text[:600] or PRESETS[key].notes})
    return PRESETS["standard"].model_copy(update={"notes": text[:600]})


def parse(value: dict | None) -> StyleSpec | None:
    """The stored spec, or None when absent or no longer valid (never raises)."""
    if not value:
        return None
    try:
        return StyleSpec.model_validate(value)
    except ValidationError:
        return None


def block(spec: StyleSpec) -> str:
    """The style as instructions every agent receives (one wording, so they agree)."""
    low, high = spec.lesson_bounds()
    # Models cannot count characters but keep to a word count; the gate measures the teaching
    # text only, so say so (a live run wrote 2,400-3,000 characters for an 1,800 ceiling).
    length = (
        f"{low}-{high} characters, about {low // 6}-{high // 6} words of teaching (the "
        "<details> answers and the sources do not count); stay under the upper bound"
        if high
        else f"at least {low} characters"
    )
    lines = [
        f"LEARNING STYLE: {spec.name}",
        f"- Learner: {spec.learner or 'as in the brief'}"
        + (f"; level: {spec.level}" if spec.level else ""),
        f"- Depth: {spec.depth}. Rigor: {spec.rigor} "
        + {
            "intuitive": "(intuition, pictures and analogies; no formal derivations or symbols "
            "the learner cannot already read)",
            "standard": "(clear explanations with the key reasoning)",
            "rigorous": "(precise definitions, derivations or proofs, and hard cases)",
        }[spec.rigor],
        f"- Format: {spec.format}: a session is about {spec.session_minutes} minutes; "
        f"a lesson is {length}.",
        f"- Tone: {spec.tone}."
        + (
            " Make it a game: quests, levels, points, streaks and playful challenges."
            if spec.gamified
            else ""
        ),
    ]
    if spec.notes:
        lines.append(f"- The learner's own words: {spec.notes}")
    lines.append(
        "This style overrides the default length, structure and register rules wherever they "
        "differ. Correctness, observable objectives and honesty never relax."
    )
    return "\n".join(lines)


STYLIST = """You are the Learning-Style Interpreter for Socrat, a platform that teaches any
subject in any style. Turn a person's free-text wish about HOW they want to learn into one
JSON learning style. Infer sensible values for anything unsaid; never refuse a style.

Fields:
- name: 2-4 word label
- learner: who the learner is (age, background); "" if unsaid
- level: the level to pitch at ("primary school", "Harvard-level undergraduate"); "" if unsaid
- depth: overview | practitioner | mastery
- format: bite (one small idea per sitting) | standard | deep (long, thorough lessons)
- session_minutes: 3-120, how long one sitting lasts
- tone: warm | playful | formal | neutral
- tutor: socratic (mostly questions) | coach (encouraging, example-led) | direct (answers first)
- rigor: intuitive (no formalism) | standard | rigorous (derivations, proofs)
- gamified: true when they want game mechanics
- notes: their wish in one sentence, in their words

Reply with one JSON object only with exactly those fields."""


async def interpret(
    engine, settings, request: str, make=None, user_id: str | None = None
) -> tuple[StyleSpec, str]:
    """(style, source): source is "agent" or "rules" (model unavailable or reply unusable)."""
    from socrat.assistant.gateway import ProviderError, make_provider
    from socrat.coursegen import roles

    text = request.strip()
    try:
        reply = await roles.ask(
            engine,
            settings,
            "stylist",
            STYLIST,
            f"Wish:\n{text}",
            1000,
            make or make_provider,
            user_id,
        )
    except ProviderError:
        return from_rules(text), "rules"
    if reply.data is not None:
        try:
            spec = StyleSpec.model_validate(
                {**reply.data, "notes": reply.data.get("notes") or text[:600]}
            )
            return spec, "agent"
        except ValidationError:
            pass
    return from_rules(text), "rules"


TUTOR_MOVES = {
    "socratic": "Mostly guide with one focused question at a time; explain directly only when "
    "asked what something means.",
    "coach": "Lead with a concrete example, story or picture, then ask one small question. "
    "Celebrate each specific step the learner gets right.",
    "direct": "Answer first, plainly, in a few sentences; then offer one quick check or the "
    "next step. Do not make the learner earn simple answers.",
}


def tutor_block(spec: StyleSpec) -> str:
    """What the tutor is told about how this learner wants to be taught (one section of the
    per-turn context; it overrides the default reply length and register)."""
    lines = [
        f'This learner chose the style "{spec.name}".',
        f"Learner: {spec.learner or 'unspecified'}. Pitch level: {spec.level or 'match them'}.",
        f"Teaching move: {TUTOR_MOVES[spec.tutor]}",
        f"Tone: {spec.tone}. Rigor: {spec.rigor}. Sessions are about {spec.session_minutes} minutes: "
        "keep each reply sized for that and end with one clear next step.",
    ]
    if spec.rigor == "intuitive":
        lines.append(
            "Avoid formulas and jargon; if a term is needed, explain it in everyday words."
        )
    if spec.rigor == "rigorous":
        lines.append("Be precise: define terms, state assumptions, and show derivations or proofs.")
    if spec.gamified:
        lines.append(
            "Frame learning as quests and levels with playful challenges and encouragement. "
            "Never state points, levels or streaks as facts about their account; Socrat's "
            "own progress numbers come only from the context."
        )
    if spec.notes:
        lines.append(f"In their words: {spec.notes}")
    lines.append(
        "This style overrides the default reply length and register. Accuracy, honesty and "
        "the help-level rules for practice problems still apply."
    )
    return "\n".join(lines)
