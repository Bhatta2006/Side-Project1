"""How a lesson is cut into pages for one learner: page size, ideas per page, page count,
how often the learner does something, and which page elements suit them.

Lessons are read one page at a time (one ``## `` section per page). How much a page holds is
not a fixed number and not a choice between "kids" and "university": it is worked out here, by
code, from everything the course knows about the learner (who they are, what they already
know, how far they want to go, how rigorous and how long a sitting is, how they like to learn,
accessibility needs), and every decision carries a reason a person can read.

Research behind the shape (from the author's knowledge, not re-checked; see
``docs/implementation/experience-plan.md`` 1.6): learner-paced segments beat one continuous
text (Mayer, segmenting), cognitive load is lower when a page carries fewer new elements
(Sweller), novices need more worked examples and experts fewer (Kalyuga, expertise reversal),
and questions between segments beat the same questions at the end (testing effect).

The numbers are starting points to calibrate against outcomes (pages finished, concept-check
results), not findings.
"""

from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field

from socrat.style.spec import StyleSpec

Register = str  # little-kid | kid | teen | general | university | professional

# Words a reader of this register can hold as one page before it stops feeling like one step.
# Children are often read to; professionals want it concise; students reading to master a
# subject accept the longest page.
BASE_WORDS = {
    "little-kid": 50,
    "kid": 110,
    "teen": 200,
    "general": 280,
    "university": 380,
    "professional": 320,
}
# Study-reading speed in words a minute (reading to learn is roughly half of everyday reading
# speed; dense university text is slower again), used only to size a lesson to a sitting.
READ_RATE = {
    "little-kid": 40,
    "kid": 70,
    "teen": 110,
    "general": 130,
    "university": 120,
    "professional": 150,
}
PRIOR = {"none": 0.85, "beginner": 0.95, "intermediate": 1.05, "advanced": 1.15}
RIGOR = {"intuitive": 0.85, "standard": 1.0, "rigorous": 1.2}
APPROACH = {"visual": 0.8, "bite-sized": 0.8, "gamified": 0.9}
BALANCE = {"practice-heavy": 0.85, "balanced": 1.0, "theory-heavy": 1.15}
# Share of a sitting spent reading the lesson; the rest is the checks between pages, the
# concept check, practice and thinking.
READING_SHARE = {"practice-heavy": 0.3, "balanced": 0.4, "theory-heavy": 0.55}
ACCESS_WORDS = 0.75  # stated reading or attention needs: smaller pages, same content
# Under 18 the page grows with the learner year by year instead of jumping between three
# groups: (age, words a page, study-reading words a minute). Between two rows the value is
# interpolated; a 9-year-old and a 12-year-old no longer get the same page.
BY_AGE: tuple[tuple[int, int, int], ...] = (
    (3, 30, 30),
    (5, 50, 40),
    (7, 80, 55),
    (9, 110, 70),
    (12, 160, 95),
    (15, 200, 110),
    (17, 250, 125),
)
MIN_WORDS, MAX_WORDS = 30, 600


def for_age(age: int) -> tuple[float, float] | None:
    """(words a page, reading rate) for a learner under 18; None for an adult."""
    if age > BY_AGE[-1][0]:
        return None
    age = max(age, BY_AGE[0][0])
    for (a0, w0, r0), (a1, w1, r1) in zip(BY_AGE, BY_AGE[1:], strict=False):
        if a0 <= age <= a1:
            t = (age - a0) / (a1 - a0)
            return w0 + t * (w1 - w0), r0 + t * (r1 - r0)
    return float(BY_AGE[-1][1]), float(BY_AGE[-1][2])


MIN_PAGES, MAX_PAGES = 2, 12


class Learner(BaseModel):
    """What the course knows about who reads it. Every field optional, so a course made by an
    admin (no request) still gets a sensible profile from its style alone."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    register: str = "general"
    age: int | None = Field(default=None, ge=3, le=110)  # when the learner gave it
    starting_level: str = "beginner"
    desired_level: str = "intermediate"
    approach: list[str] = Field(default_factory=list, max_length=8)
    balance: str = "balanced"
    minutes_per_day: int | None = Field(default=None, ge=1, le=480)
    accessibility: list[str] = Field(default_factory=list, max_length=6)


@dataclass(frozen=True)
class PageProfile:
    words: tuple[int, int]  # per page, a range the writer aims for
    ideas: int  # new ideas a page may introduce
    pages: tuple[int, int]
    check_every: int  # a check after every n pages
    elements: tuple[str, ...]  # page elements that suit this learner (see ELEMENTS)
    reasons: list[str] = field(default_factory=list)


# Page elements and how a writer produces each one so the lesson page renders it
# (apps/web/src/components/markdown.tsx: ### headings become margin cards; a quote after
# "Try it before reading the reasoning" is hidden until asked for; a code span alone is a
# formula card; Markdown tables render as tables).
ELEMENTS = {
    "story": "a short story or game scene the idea lives in (plain paragraphs)",
    "picture-words": "a picture painted in words: what the learner would see or hold",
    "example": 'a "### Worked example" card, worked step by step',
    "check": 'a "### Quick check" card: one question, answer in a <details> block',
    "insight": 'a "### Why this works" card: the reason, in two or three sentences',
    "mistake": 'a "### Common mistakes" card: the tempting wrong idea and why it fails',
    "compare": 'a "### Compare" card, or a small Markdown table of the cases side by side',
    "steps": 'a "### Steps" card: the method as a numbered list',
    "reveal": 'a line "Try it before reading the reasoning." then the reasoning as a "> " quote, '
    "which stays hidden until the learner opens it",
    "formula": "a key formula alone on its own line as `code`, then what each symbol means",
    "derivation": "a derivation or proof kept behind the reveal above, so it is there on request",
    "table": "a Markdown table when values or cases are compared",
}


def learner_of(intent_or_none, style: StyleSpec | None) -> Learner:
    """A ``Learner`` from a parsed request (any object with the intent's fields) or, without
    one, from the course style's words."""
    if intent_or_none is not None:
        i = intent_or_none
        minutes = getattr(i, "minutes_per_day", None)
        age = getattr(i, "age", None)
        return Learner(
            register=getattr(i, "register", "general"),
            age=age if isinstance(age, int) and 3 <= age <= 110 else None,
            starting_level=getattr(i, "starting_level", "beginner"),
            desired_level=getattr(i, "desired_level", "intermediate"),
            approach=list(getattr(i, "approach", []))[:8],
            balance=getattr(i, "balance", "balanced"),
            minutes_per_day=max(1, min(480, minutes)) if isinstance(minutes, int) else None,
            accessibility=[str(a)[:200] for a in getattr(i, "accessibility", [])][:6],
        )
    if style is None:
        return Learner()
    words = f"{style.learner} {style.level}".lower()
    register = "general"
    if any(w in words for w in ("toddler", "preschool", "under 6", "5 year")):
        register = "little-kid"
    elif any(w in words for w in ("child", "kid", "primary", "under 1")):
        register = "kid"
    elif any(w in words for w in ("teen", "secondary", "high school")):
        register = "teen"
    elif any(w in words for w in ("university", "undergraduate", "graduate", "college")):
        register = "university"
    elif "professional" in words:
        register = "professional"
    approach = ["gamified"] if style.gamified else []
    if style.format == "bite":
        approach.append("bite-sized")
    return Learner(register=register, approach=approach, minutes_per_day=style.session_minutes)


def profile(learner: Learner, style: StyleSpec | None = None) -> PageProfile:
    """The page profile for this learner, every number with its reason."""
    reasons: list[str] = []
    register = learner.register if learner.register in BASE_WORDS else "general"
    words, rate = float(BASE_WORDS[register]), float(READ_RATE[register])
    aged = for_age(learner.age) if learner.age else None
    if aged is not None:
        words, rate = aged
        reasons.append(f"Pages start at about {int(words)} words for a {learner.age}-year-old.")
    else:
        reasons.append(f"Pages start at about {int(words)} words for a {register} reader.")

    def scale(factor: float, why: str) -> None:
        nonlocal words
        if factor != 1.0:
            words *= factor
            reasons.append(f"{'Smaller' if factor < 1 else 'Larger'} pages: {why}.")

    scale(PRIOR.get(learner.starting_level, 1.0), f"starting {learner.starting_level}")
    rigor = style.rigor if style else "standard"
    scale(RIGOR[rigor], f"{rigor} rigor")
    for a in learner.approach:
        if a in APPROACH:
            scale(APPROACH[a], f"asked for {a}")
    scale(BALANCE.get(learner.balance, 1.0), learner.balance)
    if learner.accessibility:
        scale(ACCESS_WORDS, "stated reading or attention needs")
    if style is not None and style.format == "deep":
        scale(1.1, "asked for deep lessons")
    per_page = max(MIN_WORDS, min(MAX_WORDS, round(words / 10) * 10))
    span = (max(MIN_WORDS, round(per_page * 0.8)), min(MAX_WORDS, round(per_page * 1.2)))

    young = register in ("little-kid", "kid")
    new = learner.starting_level == "none"
    expert = register in ("university", "professional") and learner.starting_level in (
        "intermediate",
        "advanced",
    )
    ideas = 1 if young or new or learner.accessibility else 2
    if expert and rigor == "rigorous":
        ideas = 3
    reasons.append(f"{ideas} new idea{'s' if ideas > 1 else ''} a page.")

    minutes = learner.minutes_per_day or (style.session_minutes if style else 30)
    share = READING_SHARE.get(learner.balance, 0.4)
    total = minutes * share * rate
    pages = max(MIN_PAGES, min(MAX_PAGES, round(total / per_page)))
    if style is not None and style.depth == "mastery":
        pages = min(MAX_PAGES, pages + 1)
    page_span = (max(MIN_PAGES, pages - 1), min(MAX_PAGES, pages + 1))
    reasons.append(
        f"{page_span[0]}-{page_span[1]} pages: a {minutes}-minute sitting, about "
        f"{round(share * 100)}% of it reading."
    )

    every = 1 if young or new or learner.balance == "practice-heavy" else 2
    reasons.append("A check after every page." if every == 1 else "A check every two pages.")

    elements = ["example", "check"]
    if young:
        elements = ["story", "picture-words", *elements]
    else:
        elements += ["insight", "mistake"]
        if learner.starting_level != "none":
            elements += ["compare", "table"]
        elements += ["steps", "reveal"]
    if rigor == "rigorous" and not young:
        elements += ["formula", "derivation"]
    if "visual" in learner.approach and "table" not in elements:
        elements.append("table")
    return PageProfile(
        words=span,
        ideas=ideas,
        pages=page_span,
        check_every=every,
        elements=tuple(dict.fromkeys(elements)),
        reasons=reasons,
    )


def block(p: PageProfile) -> str:
    """The profile as instructions for the lesson writer (and context for the reviewer)."""
    lines = [
        "LESSON PAGES: the learner reads one '## ' section at a time, so each '## ' section is "
        "one page.",
        f"- Write {p.pages[0]}-{p.pages[1]} pages; each about {p.words[0]}-{p.words[1]} words, "
        f"introducing at most {p.ideas} new idea{'s' if p.ideas > 1 else ''}.",
        "- Page 1 opens with a question the learner can try to answer before reading on.",
        f"- {'Every page' if p.check_every == 1 else 'Every second page'} ends with a quick "
        "check the learner does.",
        "- Use page elements instead of more plain paragraphs, choosing what fits each idea:",
        *[f"  - {name}: {ELEMENTS[name]}" for name in p.elements],
        "- The last page is 'Check yourself' with the answers inside a <details> block.",
        "These sizes come from who the learner is; they replace the default length rules.",
    ]
    return "\n".join(lines)


def check(text: str, p: PageProfile) -> list[str]:
    """Deterministic page gates, with room for a writer that cannot count words exactly: a page
    may run to 1.6 times its size or down to 0.4 times; the page count may be one short or two
    over. The closing 'Check yourself' page is not sized."""
    import re

    parts = re.split(r"^## ", text, flags=re.MULTILINE)[1:]
    sized = [s for s in parts if not re.match(r"(check yourself|self-check|quick check)", s, re.I)]
    problems = []
    if not p.pages[0] - 1 <= len(parts) <= p.pages[1] + 2:
        problems.append(
            f"Write {p.pages[0]}-{p.pages[1]} '## ' pages for this learner; there are {len(parts)}."
        )
    for section in sized:
        body = re.sub(r"<details.*?</details>", "", section, flags=re.DOTALL | re.IGNORECASE)
        title, _, rest = body.partition("\n")
        n = len(rest.split())
        if n > p.words[1] * 1.6:
            problems.append(
                f"Page '{title.strip()[:60]}' has about {n} words; this learner's pages hold "
                f"about {p.words[0]}-{p.words[1]}. Split it into two pages."
            )
        elif n < p.words[0] * 0.4:
            problems.append(
                f"Page '{title.strip()[:60]}' has about {n} words; this learner's pages hold "
                f"about {p.words[0]}-{p.words[1]}. Join it with the next page or develop it."
            )
    return problems
