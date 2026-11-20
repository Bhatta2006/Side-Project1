"""What a learning request needs from a course, split in two.

``CourseSpec`` holds the hard requirements: fields that change the lessons and assessments
themselves (topic, depth, frame, assessment kind, rigor, mode, language). Two requests with
compatible specs can share one course. Everything a learner's own sessions can absorb (their
daily minutes, where they start, their Lesson 0 signals, their own words) is the overlay, kept
private to their enrollment.

Code only, no model: wording differences ("first-degree" / "linear", "mystery" / "detective")
are normalised here, so they never decide whether a course is reused.
"""

import hashlib
import json
import re

from pydantic import BaseModel, Field

from socrat.coursegen.search import content_words

VERSION = "brain-1"  # stored with every decision so a later matcher can be told apart

LEVELS = ("none", "beginner", "intermediate", "advanced", "expert")
CHILD_REGISTERS = {"little-kid", "kid", "teen"}

# How the whole course is told. Order matters: the first kind that matches wins.
FRAMES: tuple[tuple[str, re.Pattern], ...] = (
    (
        "investigation",
        re.compile(
            r"\b(detectives?|myster(y|ies)|investigat\w*|sleuth\w*|crimes?|whodunn?its?|"
            r"case ?files?|clues?)\b"
        ),
    ),
    ("game", re.compile(r"\b(games?|gamif\w*|quests?|level(ing)? up)\b")),
    ("story", re.compile(r"\b(story|stories|storytelling|narratives?|adventures?)\b")),
)
ASSESSMENTS: tuple[tuple[str, re.Pattern], ...] = (
    ("proof", re.compile(r"\b(proofs?|prove|derivations?|derive)\b")),
    ("drill", re.compile(r"\b(drills?|timed|speed ?runs?|flash ?cards?|rapid[- ]fire)\b")),
    ("project", re.compile(r"\b(through|by|with) (building |real |small )?projects?\b")),
)
RIGOROUS = re.compile(
    r"\b(rigou?r\w*|proofs?|derivations?|university[- ]level|formal(ly)?|mathematically precise)\b"
)
INTUITIVE = re.compile(
    r"\b(intuiti\w+|no (maths?|formulas?|equations|jargon)|simple terms|plain words|"
    r"like i'?m (5|five))\b"
)
# Personal context that must never reach a course another learner could be served.
PRIVATE = re.compile(
    r"\b(my|our) (company|startup|employer|client|clients|boss|team'?s?|thesis|dissertation|"
    r"codebase|repo|repository|dataset|data|spreadsheet|notes|files?)\b|"
    r"[\w.+-]+@[\w-]+\.[\w.]+|https?://",
    re.I,
)

# Words that describe how or why someone learns, not what: dropped from the topic so
# "linear equations through detective cases" and "linear equations" name the same topic.
NOT_TOPIC = frozenset(
    "teach learn learning help want need like would understand master get solve solving "
    "study studying through using use via way short quick daily day days minutes minute hour "
    "hours week weeks cases case have has had know knows make ten five fifteen twenty "
    "thirty forty sixty every each same style mode please also already some them these those "
    "who whom which while then than just only really very want wants able start starting "
    "zero scratch fundamental fundamentals essential essentials exam exams test tests "
    "drill drills timed".split()
)
_FRAME_WORDS = frozenset(
    "detective detectives mystery mysteries investigation investigations investigate sleuth "
    "crime crimes whodunit clue clues game games gamified quest quests story stories "
    "storytelling narrative narratives adventure adventures".split()
)
# Same idea, different words. Applied to whole phrases before the topic is tokenised.
PHRASES = (
    (re.compile(r"\b(first|1st)[- ]degree\b"), "linear"),
    (re.compile(r"\bmaths?\b"), "mathematics"),
    (re.compile(r"\bstats\b"), "statistics"),
    (re.compile(r"\bprob\b"), "probability"),
    (re.compile(r"\bc\+\+"), "cpp"),
    (re.compile(r"\bjs\b"), "javascript"),
    (re.compile(r"\bml\b"), "machine learning"),
)


def _stem(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def normalise(text: str) -> str:
    out = text.lower()
    for pattern, repl in PHRASES:
        out = pattern.sub(repl, out)
    return out


def topic_of(subject: str) -> str:
    """The stemmed content words of a subject, sorted; style and time words removed. Falls back
    to the subject as written when nothing is left ("C", "Go")."""
    words = {
        _stem(w)
        for w in content_words(normalise(subject))
        if w not in NOT_TOPIC and w not in _FRAME_WORDS
    }
    words -= {_stem(w) for w in NOT_TOPIC | _FRAME_WORDS}
    if words:
        return " ".join(sorted(words))[:160]
    return re.sub(r"[^a-z0-9+#]+", " ", subject.lower()).strip()[:160] or "general"


class CourseSpec(BaseModel):
    """The hard requirements of a course. A field left empty was not asked for."""

    root: str
    topic: str
    depth: str = "intermediate"  # Intent.desired_level
    entry: str = "none"  # what the course assumes the learner already knows (Intent.starting_level)
    frame: str = "none"  # none | investigation | game | story
    assessment: str = "quiz"  # quiz | drill | proof | project
    rigor: str = "balanced"  # intuitive | balanced | rigorous
    mode: str | None = None  # Lesson 0 mode: sprint | builder | explorer
    band: str = "standard"  # bite (<=12 min sessions) | standard | long
    language: str = "en"
    audience: str = "general"  # Intent.register: age and formality
    code_languages: list[str] = Field(default_factory=list)

    def key(self) -> str:
        """Identical specs share a key; ``entry`` and ``band`` are compared by order, not
        equality, but are still part of the key so an exact match ranks first."""
        return hashlib.sha256(
            json.dumps(self.model_dump(mode="json"), sort_keys=True).encode()
        ).hexdigest()


def band_of(minutes: int | None) -> str:
    if not minutes:
        return "standard"
    return "bite" if minutes <= 12 else "standard" if minutes <= 40 else "long"


def _first(patterns, text: str, default: str) -> str:
    return next((name for name, p in patterns if p.search(text)), default)


def derive(text: str, intent: dict, root: str, profile: dict | None = None) -> CourseSpec:
    """The spec of a request: from the learner's own words (``text``), the parsed intent and,
    when it came through Lesson 0, the profile. Only learner-originated text decides the frame,
    assessment and rigor: the onboarding notes in ``style_request`` describe a door and gaps,
    which are the learner's overlay, not the course."""
    goal = (profile or {}).get("learner_goal") or {}
    wish = text if profile else " ".join([text, str(intent.get("style_request") or "")])
    wish = wish.lower()
    approach = set(intent.get("approach") or [])
    frame = _first(FRAMES, wish, "game" if "gamified" in approach else "none")
    assessment = _first(ASSESSMENTS, wish, "quiz")
    rigor = (
        "rigorous"
        if RIGOROUS.search(wish)
        else "intuitive"
        if INTUITIVE.search(wish)
        else "balanced"
    )
    minutes = goal.get("daily_time_budget_mins") or intent.get("minutes_per_day")
    start = str(intent.get("starting_level") or "none")
    return CourseSpec(
        root=root,
        topic=topic_of(str(intent.get("subject") or text)),
        depth=str(intent.get("desired_level") or "intermediate"),
        entry=start if start in LEVELS else "none",
        frame=frame,
        assessment=assessment,
        rigor=rigor,
        mode=goal.get("learning_mode"),
        band=band_of(minutes),
        language=str(intent.get("language") or "en"),
        audience=str(intent.get("register") or "general"),
        code_languages=sorted(intent.get("code_languages") or []),
    )


def is_private(text: str, material: str | None) -> bool:
    """A request whose course would carry personal context (their notes, their company's data):
    it is built for them alone and never served to anyone else."""
    return bool((material or "").strip()) or bool(PRIVATE.search(text))


def overlay(text: str, intent: dict, profile: dict | None) -> dict:
    """What applies only to this learner. Stored on their match row and copied to their
    enrollment; never written to a course another learner can take."""
    goal = (profile or {}).get("learner_goal") or {}
    personal = (profile or {}).get("personalization") or {}
    cal = (profile or {}).get("calibration") or {}
    out = dict(
        request=text[:500],
        minutes=goal.get("daily_time_budget_mins") or intent.get("minutes_per_day"),
        starting_level=intent.get("starting_level"),
        deadline=intent.get("deadline"),
        mode=goal.get("learning_mode"),
        door=personal.get("primary_analogy_domain"),
        tone=personal.get("preferred_tone"),
        calibration={
            k: cal.get(k)
            for k in ("calibrated", "concept_probed", "outcome", "detected_gaps", "pace_level")
            if k in cal
        },
    )
    return {k: v for k, v in out.items() if v not in (None, "", {}, [])}
