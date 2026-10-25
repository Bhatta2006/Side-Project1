"""Every tunable number of the adaptive quiz in one frozen object.

Values follow content.md §8.5 and §8.8 with M0's decisions: track targets are
Foundations 0.80, Interview 0.72, Competitive 0.65 (D5, the PRD's floor), and θ never
becomes a mastery state (D4).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal

from socrat.mastery.model import EvidenceKind

Track = Literal["foundations", "interview", "competitive"]
Mode = Literal["placement", "concept_check", "review", "checkpoint", "weekly", "contest"]
Pool = Literal["practice", "assessment"]

TRACKS: tuple[Track, ...] = ("foundations", "interview", "competitive")
COURSE_TRACK: Mapping[str, Track] = MappingProxyType(
    {"zero": "foundations", "dsa": "interview", "cp": "competitive"}
)


@dataclass(frozen=True)
class ModeSpec:
    min_items: int
    max_items: int
    pool: Pool = "practice"
    evidence: EvidenceKind | None = None  # None: the mode writes no mastery evidence
    hints: bool = False
    interleave: bool = False  # alternate patterns so the same one is not served twice in a row
    calibrated_only: bool = False  # assessment: calibrated items only, else fail closed (D3)
    win_first: bool = False  # cold start: first items one band below the estimate
    rating_ceiling: bool = False  # contest: never above the learner's current rating band
    stop_rules: bool = False  # concept check: ceiling and stability stop rules


def _modes() -> Mapping[Mode, ModeSpec]:
    def assessment(low: int, high: int, evidence: EvidenceKind | None) -> ModeSpec:
        return ModeSpec(low, high, "assessment", evidence, interleave=True, calibrated_only=True)

    return MappingProxyType(
        {
            "concept_check": ModeSpec(
                6, 10, evidence="quiz", hints=True, win_first=True, stop_rules=True
            ),
            "review": ModeSpec(
                3, 5, evidence="review", hints=True, interleave=True, win_first=True
            ),
            "contest": ModeSpec(5, 5, evidence="quiz", rating_ceiling=True),
            "placement": assessment(12, 20, None),  # priors only, no mastery
            "checkpoint": assessment(13, 18, "checkpoint"),
            "weekly": assessment(12, 18, "quiz"),
        }
    )


@dataclass(frozen=True)
class EngineConfig:
    # Item rating prior per band 1..7 (§8.5 table).
    band_prior: tuple[int, ...] = (800, 950, 1100, 1250, 1400, 1550, 1700)
    target: Mapping[Track, float] = field(
        default_factory=lambda: MappingProxyType(
            {"foundations": 0.80, "interview": 0.72, "competitive": 0.65}
        )
    )
    start_theta: Mapping[Track, float] = field(
        default_factory=lambda: MappingProxyType(
            {"foundations": 900.0, "interview": 1000.0, "competitive": 1100.0}
        )
    )
    # Band a concept check aims to see answered independently before stopping early.
    ceiling_band: Mapping[Track, int] = field(
        default_factory=lambda: MappingProxyType(
            {"foundations": 4, "interview": 5, "competitive": 5}
        )
    )
    # Prior mastery shifts the starting θ by at most this much (cold start).
    prior_spread: float = 200.0
    # K_u: 40 for the first 10 answers, 24 up to 30, then 16.
    k_user_steps: tuple[tuple[int, float], ...] = ((10, 40.0), (30, 24.0))
    k_user_floor: float = 16.0
    # K_i = k_item_base / (1 + n / k_item_halflife) + k_item_floor.
    k_item_base: float = 30.0
    k_item_halflife: float = 20.0
    k_item_floor: float = 6.0
    # Score by hints used before a correct answer: 0, 1, 2, 3+.
    hint_scores: tuple[float, ...] = (1.0, 0.6, 0.3, 0.1)
    theta_min: float = 600.0
    theta_max: float = 2000.0
    # Unmastered prerequisites cap the band (and so θ) a learner is served.
    prerequisite_cap_band: int = 5
    # θ may sit this far above the prior of the highest allowed band.
    band_headroom: float = 150.0
    tie_tolerance: float = 0.05
    exposure_cap: float = 0.2
    exposure_min_learners: int = 20  # below this the share is noise, so no cap applies
    exposure_window_s: int = 7 * 86_400
    format_run: int = 2  # a format may appear at most this many times in a row
    max_jump: int = 2
    cold_start_items: int = 2
    step_down_after: int = 3  # consecutive wrongs before dropping a band with a micro-lesson
    stable_min_items: int = 8
    stable_window: int = 3
    stable_points: float = 15.0
    practice_share: float = 0.70
    # Assessment modes need this many calibrated assessment items per requested concept.
    assessment_min_per_concept: int = 3
    modes: Mapping[Mode, ModeSpec] = field(default_factory=_modes)

    def prior(self, band: int) -> float:
        return float(self.band_prior[band - 1])


DEFAULT = EngineConfig()
