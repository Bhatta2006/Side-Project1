"""Notice when a learner is stuck on a concept, say why, and pick the next intervention.

Several weak signals together count as stuck; one bad day does not. The intervention
ladder escalates one rung at a time, in two tiers:

- in-concept support (worked example, simpler explanation, tutor check-in) the planner
  adds on its own, because it changes how a concept is taught, not the roadmap;
- roadmap changes (probe prerequisites, repair a prerequisite, set the concept aside)
  which are only ever *proposed*; the learner decides.
"""

from dataclasses import asdict, dataclass

from socrat.adaptive.profile import SkillProfile
from socrat.mastery.model import DAY

LONG_DAYS = 5
MANY_ATTEMPTS = 6
HINT_HEAVY = 0.6
SLOW = 2.0

# Rungs, mildest first: (name, needs the learner's yes, minimum severity).
LADDER: tuple[tuple[str, bool, int], ...] = (
    ("example", False, 1),  # worked example of the concept
    ("explain", False, 1),  # the lesson re-explained more simply
    ("probe", True, 1),  # quick check of the prerequisites to find the real gap
    ("repair", True, 1),  # refresh the weak prerequisite first
    ("checkin", False, 2),  # talk it through with the tutor
    ("defer", True, 3),  # set it aside, continue, come back later
)
SIGNAL_WORDS = {
    "long_time": "you've been on it for several days",
    "plateau": "your results have levelled off",
    "many_attempts": "it has taken many attempts",
    "hint_heavy": "most successes needed hints",
    "slow": "it takes much longer than planned",
    "repeat_mistake": "the same mistake keeps coming back",
    "failing": "several recent attempts missed",
}
MODE_WORDS = {
    "concept_gap": "the idea itself isn't solid yet",
    "logic": "the approach is close but the logic slips on some cases",
    "performance": "solutions work but are too slow",
    "implementation": "the code crashes at runtime",
    "syntax": "the language syntax is getting in the way",
}


@dataclass(frozen=True)
class Stuck:
    concept: str
    severity: int  # 1 mild .. 3 severe
    signals: tuple[str, ...]
    failure_mode: str
    summary: str

    def to_dict(self) -> dict:
        return asdict(self)


def signals(profile: SkillProfile, now: int) -> list[str]:
    found = []
    if profile.first_seen_at and now - profile.first_seen_at >= LONG_DAYS * DAY:
        if profile.active_days >= 3:
            found.append("long_time")
    if profile.plateau:
        found.append("plateau")
    if profile.attempts >= MANY_ATTEMPTS and profile.band in {"needs_practice", "developing"}:
        found.append("many_attempts")
    if profile.hint_dependence >= HINT_HEAVY and profile.attempts >= 3:
        found.append("hint_heavy")
    if profile.speed is not None and profile.speed >= SLOW:
        found.append("slow")
    if any(n >= 2 for n in profile.misconceptions.values()):
        found.append("repeat_mistake")
    if profile.recent_failures >= 3:
        found.append("failing")
    return found


def failure_mode(profile: SkillProfile) -> str:
    """Why attempts fail (D4): the code's verdicts, else the concept itself."""
    modes = {k: v for k, v in profile.failure_modes.items() if k != "other"}
    if modes and (profile.recent_failures < 2 or profile.band != "needs_practice"):
        return max(sorted(modes), key=lambda k: modes[k])
    return "concept_gap"


def detect(profile: SkillProfile, now: int) -> Stuck | None:
    if profile.band in {"strong", "not_started", "likely_known"}:
        return None
    found = signals(profile, now)
    if len(found) < 2 and "failing" not in found:
        return None
    severity = min(3, max(1, len(found) - 1))
    mode = failure_mode(profile)
    reasons = ", ".join(SIGNAL_WORDS[s] for s in found[:3])
    return Stuck(
        profile.concept,
        severity,
        tuple(found),
        mode,
        f"Stuck signs: {reasons}. Likely cause: {MODE_WORDS[mode]}.",
    )


def next_rung(
    stuck: Stuck, tried: set[str], has_weak_prereq: bool, has_prereqs: bool = True
) -> tuple[str, bool] | None:
    """The mildest untried rung that fits; ``tried`` holds rung names already used.

    Every rung used without getting unstuck raises the effective severity, so a learner who
    keeps missing after the gentle rungs reaches the tutor and then the option to move on,
    instead of retaking the same check forever.
    """
    used = {r for r, _, _ in LADDER} & tried
    severity_now = min(3, stuck.severity + (len(used) + 1) // 2)
    for rung, proposal, severity in LADDER:
        if rung in tried or (rung == "repair" and not has_weak_prereq):
            continue
        if rung == "probe" and not has_prereqs:
            continue  # nothing underneath to probe
        if severity_now < severity:
            return None
        return rung, proposal
    return None
