"""How strict Socrat is with one learner: their choice, not a fixed policy.

Three modes. Each changes only *friction*: whether later modules wait for a checkpoint,
how long a retry waits after a miss, and how soon the tutor may show a full solution.
None of them changes what counts as evidence. Pass marks, mastery and the record of
independent versus assisted work are the same in every mode, so progress stays honest
whichever mode the learner picks.

Pure data: callers look the learner's mode up and pass the policy along.
"""

from dataclasses import dataclass
from typing import Literal

from socrat.mastery.model import DAY

Mode = Literal["relaxed", "balanced", "strict"]
MODES: tuple[Mode, ...] = ("relaxed", "balanced", "strict")
DEFAULT: Mode = "balanced"


@dataclass(frozen=True)
class Policy:
    mode: Mode
    # Later modules stay shut until their checkpoint (and any transfer check) is passed.
    locks_modules: bool
    # Seconds before a failed checkpoint or transfer check may be tried again.
    checkpoint_cooldown: int
    transfer_cooldown: int
    # Failed submissions needed before the tutor may walk through the full solution.
    reveal_min_failed_submits: int
    # Strict also wants the learner to have worked through the hint ladder first.
    reveal_needs_hint_ladder: bool
    # One line for the tutor's instructions: how it should sound with this learner.
    tutor_line: str


POLICIES: dict[Mode, Policy] = {
    "relaxed": Policy(
        mode="relaxed",
        locks_modules=False,
        checkpoint_cooldown=0,
        transfer_cooldown=0,
        reveal_min_failed_submits=1,
        reveal_needs_hint_ladder=False,
        tutor_line=(
            "This learner chose a relaxed style. Be encouraging and easygoing, offer hints "
            "readily, and never make them feel tested."
        ),
    ),
    "balanced": Policy(
        mode="balanced",
        locks_modules=True,
        checkpoint_cooldown=0,
        transfer_cooldown=0,
        reveal_min_failed_submits=1,
        reveal_needs_hint_ladder=False,
        tutor_line=(
            "This learner chose a balanced style. Be warm, let them think first, and help "
            "without fuss once they have tried."
        ),
    ),
    "strict": Policy(
        mode="strict",
        locks_modules=True,
        checkpoint_cooldown=DAY,
        transfer_cooldown=DAY,
        reveal_min_failed_submits=2,
        reveal_needs_hint_ladder=True,
        tutor_line=(
            "This learner chose a strict style. Be demanding and precise, hold back answers, "
            "and push them to do the thinking."
        ),
    ),
}


def normalize(value: str | None) -> Mode:
    return value if value in MODES else DEFAULT  # type: ignore[return-value]


def policy(value: str | None) -> Policy:
    """The policy for a stored mode; unknown or unset means the default."""
    return POLICIES[normalize(value)]
