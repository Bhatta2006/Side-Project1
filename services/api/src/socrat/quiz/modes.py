"""Quiz modes around selection: availability, cold start, stop rules, roll-up, summary.

Assessment modes (placement, checkpoint, weekly) use calibrated assessment items only.
Until enough exist for every requested concept the engine declines them and the current
services run unchanged (M0 decision D3).
"""

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass

from socrat.quiz.config import DEFAULT, EngineConfig, ModeSpec, Track
from socrat.quiz.pools import Item
from socrat.quiz.rating import clamp
from socrat.quiz.selection import Step, answered


def available(
    mode: ModeSpec, concepts: list[str], items: list[Item], cfg: EngineConfig = DEFAULT
) -> bool:
    """Whether the engine may run this mode; False means use the existing service."""
    if not mode.calibrated_only:
        return True
    counts = Counter(
        i.concept
        for i in items
        if i.pool == mode.pool and i.status == "calibrated" and i.concept in concepts
    )
    return bool(concepts) and all(counts[c] >= cfg.assessment_min_per_concept for c in concepts)


def initial_theta(track: Track, prior_mean: float | None, cfg: EngineConfig = DEFAULT) -> float:
    """Track default, shifted by prior mastery (placement or evidence) when there is any."""
    start = cfg.start_theta[track]
    if prior_mean is None:
        return start
    shift = clamp((prior_mean - 0.5) * 2 * cfg.prior_spread, -cfg.prior_spread, cfg.prior_spread)
    return start + shift


def ceiling(track: Track, scope_items: list[Item], max_band: int, cfg: EngineConfig = DEFAULT):
    """Band a concept check must reach to stop early, capped by what the pool holds."""
    highest = max((i.band for i in scope_items), default=1)
    return min(cfg.ceiling_band[track], highest, max_band)


def stop_reason(
    steps: list[Step], mode: ModeSpec, ceiling_band: int, cfg: EngineConfig = DEFAULT
) -> str | None:
    served = len(steps)
    if served >= mode.max_items:
        return "max_items"
    done = answered(steps)
    if mode.max_wrong is not None and sum(s.outcome == "wrong" for s in done) >= mode.max_wrong:
        return "strikes"
    if not mode.stop_rules or served < mode.min_items:
        return None
    if mode.paced:
        right = sum(s.outcome == "correct" for s in done)
        hard = sum(1 for s in done if s.independent and s.band >= ceiling_band)
        if hard >= cfg.testout_hard_needed and right / len(done) >= cfg.testout_pass:
            return "ceiling"
        return None
    tail = done[-2:]
    if len(tail) == 2 and all(s.independent and s.band >= ceiling_band for s in tail):
        return "ceiling"
    window = done[-cfg.stable_window :]
    if (
        served >= cfg.stable_min_items
        and len(window) == cfg.stable_window
        and len({s.pattern for s in window}) == 1
        and window[0].theta_before is not None
        and window[-1].theta_after is not None
        and abs(window[-1].theta_after - window[0].theta_before) < cfg.stable_points
    ):
        return "stable"
    return None


def concept_ability(
    thetas: Mapping[str, float],
    weights: Mapping[str, float] | None = None,
    critical: frozenset[str] = frozenset(),
) -> float | None:
    """Weighted mean of pattern θ, capped by the weakest critical pattern (§8.5 roll-up)."""
    if not thetas:
        return None
    w = {p: (weights or {}).get(p, 1.0) for p in thetas}
    total = sum(w.values())
    mean = (
        sum(thetas[p] * w[p] for p in thetas) / total
        if total > 0
        else sum(thetas.values()) / len(thetas)
    )
    weakest = [thetas[p] for p in critical if p in thetas]
    return min([mean, *weakest])


@dataclass(frozen=True)
class Summary:
    served: int
    answered: int
    independent: int
    assisted: int
    wrong: int
    skipped: int
    top_band: int | None  # highest band with an independent correct
    top_independent: int  # independent corrects at that band
    top_answered: int  # answers at that band
    formats: tuple[str, ...]  # formats with an independent correct

    @property
    def headline(self) -> str:
        """Evidence, not a score: "3 of 3 independent at band 4"."""
        if self.top_band is None:
            return "No independent answers yet"
        return f"{self.top_independent} of {self.top_answered} independent at band {self.top_band}"


def summarise(steps: list[Step]) -> Summary:
    done = answered(steps)
    wins = [s for s in done if s.independent]
    top = max((s.band for s in wins), default=None)
    return Summary(
        served=len(steps),
        answered=len(done),
        independent=len(wins),
        assisted=sum(1 for s in done if s.outcome == "correct" and s.hints > 0),
        wrong=sum(1 for s in done if s.outcome == "wrong"),
        skipped=len(steps) - len(done),
        top_band=top,
        top_independent=sum(1 for s in wins if s.band == top),
        top_answered=sum(1 for s in done if s.band == top),
        formats=tuple(sorted({s.format for s in wins})),
    )
