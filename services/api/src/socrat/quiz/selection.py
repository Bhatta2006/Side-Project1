"""Choosing the next item (content.md §8.5 "Selection").

1. Candidates: the mode's pool, the requested patterns, unseen, the learner's language.
2. Bands: hard limits (never more than two bands from the last item, never higher after a
   wrong answer, never above the prerequisite cap) and a preferred range from the ladder:
   two unassisted corrects at the current band → at least one band up; one wrong → repair
   at the same or one lower band, preferring the missed misconception; three wrongs → one
   band down with the pattern's micro-lesson. Cold start serves one band below the estimate.
3. Within the band closest to the preferred range: not over-exposed, no format three times
   in a row, and (interleaved modes) not the pattern just served. These relax, softest
   first, when nothing is left; the ladder always wins over variety.
4. Among those, take the one whose P is nearest the track
   target, breaking ties within ±0.05 with a seeded choice.
"""

import random
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

from socrat.quiz.config import DEFAULT, EngineConfig, ModeSpec, Track
from socrat.quiz.pools import Item
from socrat.quiz.rating import band_for, p_correct

Outcome = Literal["correct", "wrong", "skipped"]


@dataclass(frozen=True)
class Step:
    """One served item and what happened."""

    item: str
    pattern: str
    band: int
    format: str
    outcome: Outcome
    hints: int = 0
    misconception: str | None = None  # of the chosen wrong option, when tagged
    theta_before: float | None = None
    theta_after: float | None = None
    seconds: int = 0  # time to answer, server-capped

    @property
    def independent(self) -> bool:
        return self.outcome == "correct" and self.hints == 0


@dataclass(frozen=True)
class Context:
    track: Track
    mode: ModeSpec
    patterns: tuple[str, ...]
    language: str
    thetas: Mapping[str, float]
    seed: str
    ratings: Mapping[str, float] = field(default_factory=dict)  # item key -> current d
    seen: frozenset[str] = frozenset()  # items this learner saw in earlier sessions
    exposure: Mapping[str, float] = field(default_factory=dict)
    max_band: int = 7
    micro_shown: bool = False


@dataclass(frozen=True)
class Ladder:
    hard: tuple[int, int]
    preferred: tuple[int, int]
    reason: str
    misconception: str | None = None
    micro: bool = False


@dataclass(frozen=True)
class Choice:
    item: Item | None
    reason: str
    p: float | None = None
    micro: str | None = None  # pattern whose micro-lesson to show before this item


def answered(steps: list[Step]) -> list[Step]:
    return [s for s in steps if s.outcome != "skipped"]


def paced_ladder(steps: list[Step], ctx: Context, cfg: EngineConfig = DEFAULT) -> Ladder:
    """Test-out pacing: start in the middle, jump on fast or streaking right answers, hold on
    slow ones, drop one band after a miss. Nothing is served below band 2 after the start."""
    top = ctx.max_band
    done = answered(steps)
    if not done:
        estimate = band_for(min(ctx.thetas[p] for p in ctx.patterns), cfg)
        start = min(top, max(3, estimate))
        return Ladder((1, top), (start, start), "testout_start")
    last = done[-1]
    cur = last.band
    if last.outcome == "wrong":
        down = max(1, cur - 1)
        return Ladder((max(1, cur - 2), cur), (down, down), "easier_after_miss")
    streak = 0
    for s in reversed(done):
        if not s.independent:
            break
        streak += 1
    fast = last.seconds <= cfg.fast_base_s + cfg.fast_per_band_s * cur
    slow = last.seconds > cfg.slow_base_s + cfg.slow_per_band_s * cur
    low, high = max(1, cur - 1), min(top, cur + cfg.max_jump)
    if slow and streak < 3:
        return Ladder((low, high), (cur, cur), "confirm_after_slow")
    step = 2 if fast or streak >= 3 else 1
    up = min(top, cur + step)
    return Ladder((low, high), (up, up), "jump_after_fast" if step == 2 else "ladder_up")


def ladder(steps: list[Step], ctx: Context, cfg: EngineConfig = DEFAULT) -> Ladder:
    if ctx.mode.paced:
        return paced_ladder(steps, ctx, cfg)
    top = ctx.max_band
    done = answered(steps)
    if not done:
        estimate = min(band_for(min(ctx.thetas[p] for p in ctx.patterns), cfg), top)
        if ctx.mode.win_first:
            # Never above the estimate before the first answer, even when easy items run out.
            start = max(1, estimate - 1)
            return Ladder((1, max(estimate, start)), (start, start), "cold_start")
        return Ladder((1, top), (estimate, estimate), "target")
    last = done[-1]
    cur = last.band
    low, high = max(1, cur - cfg.max_jump), min(top, cur + cfg.max_jump)
    if last.outcome == "wrong":
        high = min(high, cur)
        wrongs = 0
        for s in reversed(done):
            if s.outcome != "wrong":
                break
            wrongs += 1
        if wrongs % cfg.step_down_after == 0:
            down = max(1, cur - 1)
            return Ladder((low, max(low, down)), (down, down), "step_down", micro=True)
        return Ladder((low, high), (max(1, cur - 1), cur), "repair", last.misconception)
    streak = 0
    for s in reversed(done):
        if not (s.independent and s.band == cur):
            break
        streak += 1
    if streak >= 2:
        up = min(cur + 1, top)
        return Ladder((low, high), (up, high), "ladder_up")
    if len(done) < cfg.cold_start_items and ctx.mode.win_first:
        return Ladder((low, high), (cur, cur), "cold_start")
    return Ladder((low, high), (low, high), "target")


def served_stems(items: list[Item], steps: list[Step]) -> set[str]:
    """Stems already asked this session (the same generated question with other values counts)."""
    keys = {s.item for s in steps}
    return keys | {i.stem for i in items if i.key in keys}


def candidates(items: list[Item], steps: list[Step], ctx: Context) -> list[Item]:
    """Items the mode may serve at all: pool, status, scope, unseen, language, new question."""
    served = served_stems(items, steps)
    scope = set(ctx.patterns)
    base = [
        i
        for i in items
        if (ctx.mode.any_pool or i.pool == ctx.mode.pool)
        and i.status != "retired"
        and (i.status == "calibrated" or not ctx.mode.calibrated_only)
        and i.pattern in scope
        and i.stem not in served
        and i.key not in ctx.seen
        and (not i.languages or ctx.language in i.languages)
    ]
    return base


def varied(pool: list[Item], steps: list[Step], ctx: Context, cfg: EngineConfig = DEFAULT):
    """Soft filters: exposure, format runs, interleaving; relaxed when nothing is left."""
    scope = set(ctx.patterns)
    recent = [s.format for s in steps[-cfg.format_run :]]
    run = recent[0] if len(recent) == cfg.format_run and len(set(recent)) == 1 else None
    last_pattern = steps[-1].pattern if steps else None
    filters = [
        lambda i: ctx.exposure.get(i.key, 0.0) < cfg.exposure_cap,
        lambda i: i.format != run,
        lambda i: not (ctx.mode.interleave and len(scope) > 1 and i.pattern == last_pattern),
    ]
    # Relax the softest filter first: interleave, then format run, then exposure.
    for keep in range(len(filters), -1, -1):
        chosen = [i for i in pool if all(f(i) for f in filters[:keep])]
        if chosen:
            return chosen
    return pool


def topup(items: list[Item], steps: list[Step], ctx: Context) -> list[Item]:
    """Below a mode's minimum, relax in order: any band, then items seen in earlier sessions.
    The assessment pool stays reserved for exams, and exam modes never relax."""
    if ctx.mode.calibrated_only or ctx.mode.paced:
        return []
    served = served_stems(items, steps)
    scope = set(ctx.patterns)
    live = [
        i
        for i in items
        if i.status != "retired"
        and i.pattern in scope
        and i.stem not in served
        and (not i.languages or ctx.language in i.languages)
    ]
    for keep in (
        lambda i: i.pool == ctx.mode.pool and i.key not in ctx.seen,
        lambda i: i.pool == ctx.mode.pool,
    ):
        pool = [i for i in live if keep(i)]
        if pool:
            return pool
    return []


def distance(band: int, span: tuple[int, int]) -> int:
    return max(span[0] - band, 0, band - span[1])


def select(
    items: list[Item], steps: list[Step], ctx: Context, cfg: EngineConfig = DEFAULT
) -> Choice:
    rule = ladder(steps, ctx, cfg)
    if ctx.mode.rating_ceiling:
        cap = min(band_for(ctx.thetas[p], cfg) for p in ctx.patterns)
        hard = (min(rule.hard[0], cap), min(rule.hard[1], cap))
        rule = Ladder(hard, (min(rule.preferred[0], cap), min(rule.preferred[1], cap)), rule.reason)
    pool = [i for i in candidates(items, steps, ctx) if rule.hard[0] <= i.band <= rule.hard[1]]
    if not pool:
        done = answered(steps)
        wrongs = sum(s.outcome == "wrong" for s in done)
        # Out of questions after repeated misses: teach first instead of serving harder ones.
        if done and done[-1].outcome == "wrong" and wrongs >= 2:
            return Choice(None, "needs_lesson")
        if len(steps) >= ctx.mode.min_items:
            return Choice(None, "exhausted")
        # Too few questions to mean anything: never stop short of the floor while the bank
        # has anything left for this learner.
        pool = topup(items, steps, ctx)
        if not pool:
            return Choice(None, "exhausted")
        rule = Ladder(rule.hard, rule.preferred, "floor")
    # The ladder overrides variety: choose the band first, then vary within it.
    gap = min(distance(i.band, rule.preferred) for i in pool)
    pool = [i for i in pool if distance(i.band, rule.preferred) == gap]
    if ctx.mode.any_pool:  # prefer the named pool (assessment: items never practised)
        pool = [i for i in pool if i.pool == ctx.mode.pool] or pool
    pool = varied(pool, steps, ctx, cfg)
    if rule.misconception:
        tagged = [i for i in pool if rule.misconception in i.misconceptions]
        pool = tagged or pool
    target = cfg.target[ctx.track]
    scored = [
        (abs(p_correct(ctx.thetas[i.pattern], ctx.ratings.get(i.key, i.d_prior)) - target), i)
        for i in pool
    ]
    best = min(score for score, _ in scored)
    ties = sorted(
        (i for score, i in scored if score <= best + cfg.tie_tolerance), key=lambda i: i.key
    )
    item = random.Random(f"{ctx.seed}:{len(steps)}").choice(ties)
    micro = item.pattern if rule.micro and not ctx.micro_shown else None
    p = p_correct(ctx.thetas[item.pattern], ctx.ratings.get(item.key, item.d_prior))
    return Choice(item, rule.reason, p, micro)
