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


_WORD = r"^[A-Za-z]+([ \-][A-Za-z]+)?$"  # one or two plain words, shown in the app


class Frame(BaseModel):
    """The way a course is taught, for any way a learner can describe: a detective story,
    only analogies, a game, projects, letters from a grandparent. ``gamified`` used to be the
    one such way the engine knew; a frame is the same idea for all of them. Writers build
    every lesson inside it, the tutor speaks inside it, and the app uses its words for the
    learner's progress. It shapes how an idea is taught, never what is true."""

    model_config = ConfigDict(extra="forbid")
    # Plain words only: the name and the three words below are shown in the app and told
    # to the tutor, so they can carry no instruction. ``method`` goes to lesson writers only.
    name: str = Field(
        min_length=2, max_length=40, pattern=r"^[A-Za-z']+([ \-][A-Za-z']+){0,2}$"
    )  # "Detective story"
    # How every lesson is built in this frame, as an instruction to the writer.
    method: str = Field(min_length=10, max_length=400)
    lesson_word: str = Field(
        default="lesson", min_length=2, max_length=20, pattern=_WORD
    )  # "case", "chapter", "level"
    module_word: str = Field(
        default="module", min_length=2, max_length=20, pattern=_WORD
    )  # "investigation", "world"
    # What a finished lesson earns, in the frame's words ("clue", "star"); "" for nothing.
    reward_word: str = Field(default="", max_length=20, pattern=r"^$|" + _WORD)


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
    frame: Frame | None = None  # how the course is taught, for any style (see ``Frame``)
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
        return (
            self.format != "bite"
            and not self.gamified
            and self.tone != "playful"
            and self.frame is None  # a plain lesson is no model for a story or a case
        )


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


# Common ways to be taught, for when no model is available to read the wish. A model reads
# any wish; these only make sure the usual ones work without one (first match wins).
_FRAMES: list[tuple[re.Pattern, Frame]] = [
    (
        re.compile(r"\b(detective|mystery|mysteries|whodunn?it|case file|investigat\w*)\b", re.I),
        Frame(
            name="Detective story",
            method="Every lesson is a case. Open with something puzzling that the learner "
            "cannot yet explain, let them gather clues, and make the lesson's idea the clue "
            "that solves it. Close the case by stating the idea plainly.",
            lesson_word="case",
            module_word="investigation",
            reward_word="clue",
        ),
    ),
    (
        re.compile(r"\b(stor(y|ies)|tale|narrative|fable|novel|adventure)\b", re.I),
        Frame(
            name="Story",
            method="Teach through one continuing story with the same characters. Each lesson "
            "is a chapter in which a character meets a problem that the lesson's idea solves. "
            "After the scene, state the idea plainly so it is never left only implied.",
            lesson_word="chapter",
            module_word="part",
            reward_word="page",
        ),
    ),
    (
        re.compile(r"\b(analog(y|ies)|metaphors?|comparisons?|everyday examples?)\b", re.I),
        Frame(
            name="Analogies",
            method="Explain every idea first through one everyday analogy the learner already "
            "knows, then map each part of the analogy to the real thing, and say where the "
            "analogy stops being true.",
            lesson_word="lesson",
            module_word="module",
            reward_word="",
        ),
    ),
    (
        re.compile(r"\b(projects?|build(ing)?|hands[\s-]?on|by (doing|making))\b", re.I),
        Frame(
            name="Projects",
            method="Every lesson builds one small, real thing. Start from what will be built, "
            "teach only the idea needed for the next step, and end with the piece working. "
            "Each lesson's piece adds to the module's project.",
            lesson_word="build",
            module_word="project",
            reward_word="piece",
        ),
    ),
    (
        re.compile(r"\b(gamif\w*|games?|quests?|levels?|video[\s-]?game)\b", re.I),
        Frame(
            name="Game",
            method="Every lesson is a level with a clear goal. Give a short challenge first, "
            "teach the idea as the move that beats it, and finish with a slightly harder "
            "challenge that uses it.",
            lesson_word="level",
            module_word="world",
            reward_word="star",
        ),
    ),
]


def frame_from_rules(request: str) -> Frame | None:
    """The frame for a wish, without a model: one of the common ones by keyword, else the
    learner's own words as the method, so no way of being taught is dropped. None only when
    there is no wish to follow."""
    text = re.sub(r"\s+", " ", request.strip())
    for pattern, frame in _FRAMES:
        if pattern.search(text):
            return frame
    if len(text) < 10:
        return None
    return Frame(
        name="Your way",
        method=f"Teach every lesson the way the learner asked, in their words: {text}"[:400],
    )


def from_rules(request: str) -> StyleSpec:
    """A preset chosen by keywords, carrying the request as notes and its frame. The fallback
    when no model is available, and the answer for the simplest wishes."""
    text = request.strip()
    frame = frame_from_rules(text)
    for pattern, key in _RULES:
        if pattern.search(text):
            return PRESETS[key].model_copy(
                update={"notes": text[:600] or PRESETS[key].notes, "frame": frame}
            )
    return PRESETS["standard"].model_copy(update={"notes": text[:600], "frame": frame})


def course_frame(brief: dict | None) -> Frame | None:
    """The frame a generated course was written in, from its stored brief; None when it has
    none or the stored one no longer validates (never raises)."""
    stored = ((brief or {}).get("style") or {}).get("frame")
    if not isinstance(stored, dict):
        return None
    try:
        return Frame.model_validate(stored)
    except ValidationError:
        return None


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
    if spec.frame:
        frame = spec.frame
        lines.append(
            f"- Teaching frame: {frame.name}. {frame.method} Keep this frame from the first "
            "line of every lesson to the last, and in its checks and questions; it decides "
            "how the idea is taught, never what is true, and the idea itself is always stated "
            f'plainly at least once. In this course a lesson is called a "{frame.lesson_word}" '
            f'and a module a "{frame.module_word}".'
        )
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
- frame: how the course is taught, for ANY way they describe (a detective story, only
  analogies, a game, projects, a cooking show, letters from a grandparent); null only when
  they asked for nothing about how. An object:
  - name: 1-3 words ("Detective story")
  - method: 1-3 sentences telling a lesson writer how to build EVERY lesson this way
  - lesson_word: what one lesson is called in this frame, one or two plain words
    ("case", "chapter", "level", "recipe"); "lesson" if nothing fits
  - module_word: what a group of lessons is called ("investigation", "part", "world")
  - reward_word: what finishing a lesson earns ("clue", "star", "page"), or ""
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
        data = {**reply.data, "notes": reply.data.get("notes") or text[:600]}
        try:
            return StyleSpec.model_validate(data), "agent"
        except ValidationError:
            pass
        # A slip in the frame alone (a word too long, a missing method) keeps everything
        # else the model understood; the frame then comes from the wish itself.
        try:
            spec = StyleSpec.model_validate({**data, "frame": None})
            return spec.model_copy(update={"frame": frame_from_rules(text)}), "agent"
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
    if spec.frame:
        lines.append(
            f"The course is taught as: {spec.frame.name}. {spec.frame.method} Speak inside "
            f'this frame (a lesson is a "{spec.frame.lesson_word}"), and step out of it '
            "whenever the learner is confused: a clear answer comes before the frame. Never "
            "invent rewards, scores or progress; those come only from the context."
        )
    if spec.notes:
        lines.append(f"In their words: {spec.notes}")
    lines.append(
        "This style overrides the default reply length and register. Accuracy, honesty and "
        "the help-level rules for practice problems still apply."
    )
    return "\n".join(lines)
