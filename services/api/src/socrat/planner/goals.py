"""What the learner's goal says about which concepts matter most (B1) and path styles (B4).

Relevance is a 0..1 weight per concept for one goal focus. The planner uses it to order
the concepts that are free to move (prerequisites always come first), and the
goal-focused style sets low-relevance concepts aside as optional. Pure data and functions.
"""

from typing import Literal

Focus = Literal["foundations"]
PathStyle = Literal["thorough", "balanced", "fast_track", "goal_focused"]
STYLES: tuple[PathStyle, ...] = ("thorough", "balanced", "fast_track", "goal_focused")
STYLE_WORDS: dict[str, tuple[str, str]] = {
    "thorough": ("Thorough", "Every concept, extra practice, no shortcuts."),
    "balanced": ("Balanced", "The full path at the pace your results set."),
    "fast_track": (
        "Fast track",
        "Skip warm-ups and offer test-outs so you can prove what you know and move on.",
    ),
    "goal_focused": (
        "Goal focused",
        "What your goal needs most comes first; lower-impact topics become optional.",
    ),
}
OPTIONAL_BELOW = 0.35


def focus_of(course_id: str, goal: dict) -> Focus:
    """The goal's focus. Every course is generated for one learner and carries its own goal in
    its brief, so no course id or goal field selects a built-in weighting any more."""
    return "foundations"


def relevance(qualified: str, course_id: str, goal: dict) -> float:
    """0..1: how much this concept serves the learner's goal. Equal for every concept until the
    engine weighs concepts against the learner's stated goal (the outline's depth tags)."""
    return 1.0


def tier(value: float) -> int:
    """Coarse tiers keep ordering stable: only clear differences move a concept."""
    return 2 if value >= 0.85 else 1 if value >= 0.5 else 0
