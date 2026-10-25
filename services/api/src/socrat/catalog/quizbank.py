"""Quiz families and bank items (Content Master Plan §8.4).

``content/quiz/<course>/<concept>/<family>.yaml`` holds one family: a generator spec, static
items, or both. Generated items get their answer from executed reference code (M4), never
from a model. Every new family declares provenance and starts provisional.

The 234 items embedded in concept files are not moved: ``legacy_items`` wraps them
read-only with a global key, a format and a band from a documented mapping.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import Field, model_validator

from socrat.catalog.patterns import PatternId, Qualified, Status, Track
from socrat.catalog.schema import Language, Model, Provenance, Slug

ItemFormat = Literal[
    "mcq",
    "output_prediction",
    "trace",
    "fill_blank",
    "parsons",
    "bug_spot",
    "edge_cases",
    "complexity",
    "classify",
    "counterexample",
    "short_answer",
]
Pool = Literal["practice", "assessment"]
FamilyId = Annotated[
    str, Field(pattern=r"^quiz:[a-z][a-z0-9-]{0,63}:[a-z][a-z0-9-]{0,63}:[a-z][a-z0-9-]{0,63}$")
]
# Existing 1-5 difficulty -> 1-7 band (M0 decision D11). Code-bearing items read code, so
# they start at band 2 (predict) at least.
BAND_FOR_DIFFICULTY = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}
LEGACY_FORMAT: dict[str, ItemFormat] = {
    "mcq": "mcq",
    "output": "output_prediction",
    "bug": "bug_spot",
}


class DistractorRule(Model):
    rule: str = Field(min_length=2, max_length=300)
    misconception: Slug


class SeedRange(Model):
    start: int = Field(ge=0)
    stop: int = Field(ge=1)

    @model_validator(mode="after")
    def ordered(self):
        if self.stop <= self.start:
            raise ValueError("seed range stop must exceed start")
        return self


class GeneratorSpec(Model):
    template: Slug | Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]
    params: dict[str, list[int | float | str]] = Field(default_factory=dict)
    reference: str = Field(min_length=1, max_length=4000)
    seeds: dict[Pool, SeedRange]

    @model_validator(mode="after")
    def pools(self):
        if set(self.seeds) != {"practice", "assessment"}:
            raise ValueError("a generator needs practice and assessment seed ranges")
        practice, assessment = self.seeds["practice"], self.seeds["assessment"]
        if practice.start < assessment.stop and assessment.start < practice.stop:
            raise ValueError("practice and assessment seed ranges must not overlap")
        return self


class BankItem(Model):
    id: Slug
    band: int = Field(ge=1, le=7)
    format: ItemFormat | None = None  # defaults to the family's format
    prompt: str = Field(min_length=5, max_length=4000)
    code: dict[Language, str] = Field(default_factory=dict)
    options: list[str] = Field(min_length=2, max_length=6)
    answer: int = Field(ge=0)
    misconceptions: list[Slug | None] = Field(default_factory=list)  # aligned with options
    explanation: str = Field(min_length=5, max_length=2000)
    pool: Pool | None = None  # None: assigned by a stable hash (M3)
    status: Status = "provisional"

    @model_validator(mode="after")
    def contract(self):
        if self.answer >= len(self.options):
            raise ValueError(f"item {self.id}: answer index out of range")
        if len(set(self.options)) != len(self.options):
            raise ValueError(f"item {self.id}: duplicate options")
        if self.misconceptions:
            if len(self.misconceptions) != len(self.options):
                raise ValueError(f"item {self.id}: misconceptions must align with options")
            if self.misconceptions[self.answer] is not None:
                raise ValueError(f"item {self.id}: the correct option has no misconception")
        return self


class QuizFamily(Model):
    id: FamilyId
    family: Slug
    concept: Qualified
    pattern: PatternId | None = None
    format: ItemFormat
    tracks: list[Track] = Field(min_length=1)
    languages: list[Language] = Field(min_length=1)
    generator: GeneratorSpec | None = None
    items: list[BankItem] = Field(default_factory=list, max_length=200)
    distractors: list[DistractorRule] = Field(default_factory=list)
    hint_ladder: list[str] = Field(default_factory=list, max_length=5)
    time_limit_s: int = Field(default=90, ge=10, le=1800)
    status: Status = "provisional"
    provenance: Provenance

    @model_validator(mode="after")
    def contract(self):
        expected = f"quiz:{self.concept}:{self.family}"
        if self.id != expected:
            raise ValueError(f"family id must be {expected}")
        if self.pattern and not self.pattern.startswith(self.concept + "/"):
            raise ValueError(f"pattern {self.pattern} is not in concept {self.concept}")
        if self.generator is None and not self.items:
            raise ValueError("a family needs a generator or static items")
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError("duplicate item id")
        for item in self.items:
            extra = set(item.code) - set(self.languages)
            if extra:
                raise ValueError(f"item {item.id}: code in undeclared languages {sorted(extra)}")
        if self.status == "calibrated" and self.provenance.review is None:
            raise ValueError("a calibrated family needs a human review record")
        return self

    def item_key(self, item_id: str) -> str:
        return f"{self.id}:{item_id}"


def load(root: Path, catalog, taxonomy: set[str]) -> dict[str, QuizFamily]:
    """Load and cross-check every family; raises CatalogError on the first problem."""
    from socrat.catalog.registry import CatalogError

    found: dict[str, QuizFamily] = {}
    if not root.exists():
        return found
    for path in sorted(root.glob("*/*/*.yaml")):
        try:
            family = QuizFamily.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        except ValueError as exc:
            raise CatalogError(f"{path}: {exc}") from exc
        course, concept, name = path.relative_to(root).with_suffix("").parts
        if (family.concept, family.family) != (f"{course}:{concept}", name):
            raise CatalogError(f"{path}: file path must match family {family.id}")
        if family.id in found:
            raise CatalogError(f"{path}: duplicate family id")
        if family.concept not in catalog.concepts:
            raise CatalogError(f"{path}: unknown concept {family.concept}")
        if (
            family.generator
            and not (root / "generators" / f"{family.generator.template}.py").exists()
        ):
            raise CatalogError(f"{path}: generator template {family.generator.template} not found")
        tags = [rule.misconception for rule in family.distractors] + [
            tag for item in family.items for tag in item.misconceptions if tag
        ]
        for tag in tags:
            if tag not in taxonomy:
                raise CatalogError(f"{path}: unknown misconception {tag}")
        found[family.id] = family
    return found


def check_patterns(families: dict[str, QuizFamily], patterns: dict) -> None:
    """A family that names a pattern must name one that exists."""
    from socrat.catalog.registry import CatalogError

    for family in families.values():
        if family.pattern and family.pattern not in patterns:
            raise CatalogError(f"{family.id}: unknown pattern {family.pattern}")


@dataclass(frozen=True)
class LegacyItem:
    """A read-only view of one concept-embedded quiz item."""

    key: str  # "<course>:<concept>:<item>", unique across the catalog
    concept: str
    item_id: str
    format: ItemFormat
    difficulty: int
    band: int
    languages: tuple[str, ...]
    status: Status = "provisional"


def legacy_items(catalog) -> list[LegacyItem]:
    items = []
    for concept_key, concept in catalog.concepts.items():
        for item in concept.quiz:
            band = BAND_FOR_DIFFICULTY[item.difficulty]
            if item.code:
                band = max(band, 2)
            items.append(
                LegacyItem(
                    key=f"{concept_key}:{item.id}",
                    concept=concept_key,
                    item_id=item.id,
                    format=LEGACY_FORMAT[item.kind],
                    difficulty=item.difficulty,
                    band=band,
                    languages=tuple(item.code),
                )
            )
    return items
