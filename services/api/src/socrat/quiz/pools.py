"""The servable item bank and its practice/assessment partition (content.md §8.9).

Every item gets one pool, fixed for its lifetime:

- a static item that names its pool keeps it;
- any other item is split by a stable hash of its global key, ~70% practice;
- a generated item's pool comes from the seed range it was drawn from, and it is served
  only when the verified manifest lists it (M4).

A concept whose hash split would leave no practice item keeps its lowest-hash item in
practice, so concept checks always have something to serve (M0 gap 8).
"""

import hashlib
from collections import defaultdict
from dataclasses import dataclass

from socrat.catalog import dialect
from socrat.catalog.quizbank import (
    BAND_FOR_DIFFICULTY,
    LEGACY_FORMAT,
    GeneratorSpec,
    QuizFamily,
)
from socrat.quiz.config import DEFAULT, EngineConfig, Pool

POOL_SALT = "socrat-pool-v1"
LANGUAGES = ("python", "cpp", "java")


@dataclass(frozen=True)
class Item:
    """One servable item, legacy or from a quiz family."""

    key: str  # global: "<course>:<concept>:<item>" or "<family id>:<item>"
    concept: str
    pattern: str  # the concept itself for items without a pattern
    family: str  # "" for legacy items
    item_id: str
    format: str
    band: int
    d_prior: float
    pool: Pool
    status: str  # provisional | calibrated | retired
    languages: tuple[str, ...] = ()  # empty: no code, any language works
    misconceptions: tuple[str | None, ...] = ()  # by authored option index
    reviewed: bool = True  # False: answers do not count as mastery evidence (§8.7)
    seed: int | None = None  # generated items: the generator seed

    @property
    def stem(self) -> str:
        """The question behind the item: every seed of one generator is the same question with
        different values, so a session serves at most one of them."""
        return f"gen:{self.family}" if self.seed is not None else self.key


def unit(key: str, salt: str = POOL_SALT) -> float:
    """A stable number in [0, 1) for ``key``; independent of process and platform."""
    digest = hashlib.sha256(f"{salt}:{key}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def pool_for_key(key: str, cfg: EngineConfig = DEFAULT) -> Pool:
    return "practice" if unit(key) < cfg.practice_share else "assessment"


def pool_for_seed(spec: GeneratorSpec, seed: int) -> Pool | None:
    """The pool a generator seed belongs to, or None outside both ranges."""
    for pool, span in spec.seeds.items():
        if span.start <= seed < span.stop:
            return pool
    return None


def band_for_difficulty(difficulty: int, has_code: bool) -> int:
    """Legacy 1–5 difficulty to a 1–7 band (D11); items with code start at band 2."""
    band = BAND_FOR_DIFFICULTY[difficulty]
    return max(band, 2) if has_code else band


def legacy_bank(catalog, cfg: EngineConfig = DEFAULT) -> list[Item]:
    """The concept-embedded items. They already write evidence today, so they count."""
    items = []
    for concept_key, concept in catalog.concepts.items():
        for q in concept.quiz:
            band = band_for_difficulty(q.difficulty, bool(q.code))
            key = f"{concept_key}:{q.id}"
            items.append(
                Item(
                    key=key,
                    concept=concept_key,
                    pattern=concept_key,
                    family="",
                    item_id=q.id,
                    format=LEGACY_FORMAT[q.kind],
                    band=band,
                    d_prior=cfg.prior(band),
                    pool=pool_for_key(key, cfg),
                    status="provisional",
                    # Same language rules as the fixed checks: tags, "In C++ ..." prompts, code.
                    languages=tuple(x for x in LANGUAGES if q.fits(x)),
                )
            )
    return items


def item_languages(family: QuizFamily, q) -> tuple[str, ...]:
    """Languages a family item may be served in: its code's, else the family's minus any
    whose syntax the prose does not speak (``7 // 2`` is Python, not C++)."""
    if q.code:
        return tuple(q.code)
    allowed = tuple(family.languages)
    spoken = dialect.spoken(q.prompt, *q.options, q.explanation)
    if not spoken:
        return allowed
    return tuple(x for x in allowed if x in spoken) or ("__none__",)


def family_bank(families: dict[str, QuizFamily], cfg: EngineConfig = DEFAULT) -> list[Item]:
    """Static family items. New content counts as evidence only after a human review."""
    items = []
    for family in families.values():
        reviewed = family.provenance.review is not None
        for q in family.items:
            key = family.item_key(q.id)
            status = "retired" if "retired" in (family.status, q.status) else q.status
            items.append(
                Item(
                    key=key,
                    concept=family.concept,
                    pattern=family.pattern or family.concept,
                    family=family.id,
                    item_id=q.id,
                    format=q.format or family.format,
                    band=q.band,
                    d_prior=cfg.prior(q.band),
                    pool=q.pool or pool_for_key(key, cfg),
                    status=status,
                    languages=item_languages(family, q),
                    misconceptions=tuple(q.misconceptions),
                    reviewed=reviewed,
                )
            )
    return items


def keep_practice(items: list[Item]) -> list[Item]:
    """Move one item per concept into practice where hashing left it with none."""
    by_concept: dict[str, list[Item]] = defaultdict(list)
    for item in items:
        by_concept[item.concept].append(item)
    moved: set[str] = set()
    for group in by_concept.values():
        if group and all(i.pool == "assessment" for i in group):
            moved.add(min(group, key=lambda i: unit(i.key)).key)
    return [
        Item(**{**item.__dict__, "pool": "practice"}) if item.key in moved else item
        for item in items
    ]


def generated_bank(catalog, cfg: EngineConfig = DEFAULT) -> list[Item]:
    """Generated items listed in the verified manifest; the seed range decides the pool."""
    from socrat.quiz.generate import framework

    root = catalog.quiz_root
    if root is None:
        return []
    manifest = framework.load_manifest(root)
    items = []
    for family in catalog.quiz_families.values():
        if family.generator is None or family.status == "retired":
            continue
        reviewed = family.provenance.review is not None
        for seed, pool, draft in framework.verified_drafts(root, family, manifest):
            items.append(
                Item(
                    key=framework.item_key(family, seed),
                    concept=family.concept,
                    pattern=family.pattern or family.concept,
                    family=family.id,
                    item_id=f"s{seed}",
                    format=draft.format or family.format,
                    band=draft.band,
                    d_prior=cfg.prior(draft.band),
                    pool=pool,
                    status=family.status,
                    languages=tuple(draft.code),
                    misconceptions=tuple(o.misconception for o in draft.options),
                    reviewed=reviewed,
                    seed=seed,
                )
            )
    return items


def bank(catalog, cfg: EngineConfig = DEFAULT) -> list[Item]:
    items = legacy_bank(catalog, cfg) + family_bank(catalog.quiz_families, cfg)
    return keep_practice(items) + generated_bank(catalog, cfg)


def summary(items: list[Item]) -> dict[str, dict[str, int]]:
    """Concept -> item count per pool, for reports and tests."""
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"practice": 0, "assessment": 0})
    for item in items:
        counts[item.concept][item.pool] += 1
    return dict(counts)
