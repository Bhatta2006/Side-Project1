"""Patterns: recognisable ways of solving a family of problems inside a concept.

``content/patterns/<course>/<concept>/<pattern>.yaml`` (Content Master Plan §3.2). A
pattern references existing concepts, problems, atoms and misconception IDs by ID only; it
never creates or edits problem content. Mastery stays at concept level (PRD §11).
"""

import re
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import Field, model_validator

from socrat.catalog.schema import Language, Model, Provenance, Slug

PatternId = Annotated[
    str, Field(pattern=r"^[a-z][a-z0-9-]{0,63}:[a-z][a-z0-9-]{0,63}/[a-z][a-z0-9-]{0,63}$")
]
Qualified = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{0,63}:[a-z][a-z0-9-]{0,63}$")]
ExternalId = Annotated[str, Field(pattern=r"^(leetcode|cf|cses):[A-Za-z0-9-]{1,120}$")]
Track = Literal["foundations", "interview", "competitive"]
Status = Literal["provisional", "calibrated", "retired"]
RECOGNISE_WORDS = 60
TEMPLATE_LINES = 25


def words(value: str) -> int:
    return len(re.findall(r"\S+", value))


class Complexity(Model):
    time: str = Field(min_length=2, max_length=60)
    space: str = Field(min_length=2, max_length=60)


class Variant(Model):
    id: Slug
    band: int = Field(ge=1, le=7)
    title: str = Field(default="", max_length=120)
    problem: str | None = None  # a native problem id or an external id listed under `problems`


class TemplateIO(Model):
    """Input and expected output that every language's template is run against."""

    stdin: str = Field(default="", max_length=2000)
    expected: str = Field(min_length=1, max_length=2000)


class PatternProblems(Model):
    native: list[Slug] = Field(default_factory=list)
    external: list[ExternalId] = Field(default_factory=list)


class Pattern(Model):
    id: PatternId
    concept: Qualified
    title: str = Field(min_length=2, max_length=120)
    tracks: list[Track] = Field(min_length=1)
    recognise: list[str] = Field(min_length=3, max_length=3)
    state: str = Field(default="", max_length=300)
    transition: str = Field(default="", max_length=300)
    base_cases: list[str] = Field(default_factory=list, max_length=6)
    complexity: Complexity
    template: dict[Language, str] = Field(default_factory=dict)  # complete programs
    template_io: TemplateIO | None = None
    variants: list[Variant] = Field(min_length=1, max_length=7)
    pitfalls: list[Slug] = Field(default_factory=list)
    atoms: list[Slug] = Field(default_factory=list)
    quiz_family: str | None = None
    problems: PatternProblems = Field(default_factory=PatternProblems)
    showcase: list[str] = Field(default_factory=list)
    status: Status = "provisional"
    provenance: Provenance  # required for all new content

    @model_validator(mode="after")
    def contract(self):
        if not self.id.startswith(self.concept + "/"):
            raise ValueError(f"pattern id {self.id} must start with its concept {self.concept}")
        if sum(words(cue) for cue in self.recognise) > RECOGNISE_WORDS:
            raise ValueError(f"recognition cues exceed {RECOGNISE_WORDS} words")
        for language, code in self.template.items():
            if len(code.splitlines()) > TEMPLATE_LINES:
                raise ValueError(f"{language} template exceeds {TEMPLATE_LINES} lines")
        bands = [v.band for v in self.variants]
        if bands != sorted(bands):
            raise ValueError("variants must run easy to hard (non-decreasing bands)")
        if len({v.id for v in self.variants}) != len(self.variants):
            raise ValueError("duplicate variant id")
        if self.status == "calibrated" and self.provenance.review is None:
            raise ValueError("a calibrated pattern needs a human review record")
        return self


def load(
    root: Path,
    catalog,
    taxonomy: set[str],
    external_ids: Callable[[], set[str]],
    families: dict | None = None,
) -> dict[str, Pattern]:
    """Load and cross-check every pattern file; raises CatalogError on the first problem."""
    from socrat.catalog.registry import CatalogError

    found: dict[str, Pattern] = {}
    if not root.exists():
        return found
    known_external: set[str] | None = None
    for path in sorted(root.glob("*/*/*.yaml")):
        try:
            pattern = Pattern.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        except ValueError as exc:
            raise CatalogError(f"{path}: {exc}") from exc
        course, concept, slug = path.relative_to(root).with_suffix("").parts
        if pattern.id != f"{course}:{concept}/{slug}":
            raise CatalogError(f"{path}: file path must match pattern id {pattern.id}")
        if pattern.id in found:
            raise CatalogError(f"{path}: duplicate pattern id")
        if pattern.concept not in catalog.concepts:
            raise CatalogError(f"{path}: unknown concept {pattern.concept}")
        for problem_id in pattern.problems.native:
            if problem_id not in catalog.problems:
                raise CatalogError(f"{path}: unknown native problem {problem_id}")
        if pattern.problems.external:
            if known_external is None:
                known_external = external_ids()
            for problem_id in pattern.problems.external:
                if problem_id not in known_external:
                    raise CatalogError(f"{path}: unknown external problem {problem_id}")
        listed = set(pattern.problems.native) | set(pattern.problems.external)
        for variant in pattern.variants:
            if variant.problem and variant.problem not in listed:
                raise CatalogError(
                    f"{path}: variant {variant.id} problem {variant.problem} is not listed "
                    "under problems"
                )
        for misconception in pattern.pitfalls:
            if misconception not in taxonomy:
                raise CatalogError(f"{path}: unknown misconception {misconception}")
        pack = catalog.atom_packs.get(pattern.concept)
        own = getattr(catalog, "pattern_atoms", {}).get(pattern.id)
        available = {atom.id for atom in pack.atoms} if pack else set()
        available |= {atom.id for atom in own.atoms} if own else set()
        for atom_id in pattern.atoms:
            if atom_id not in available:
                raise CatalogError(f"{path}: unknown atom {atom_id} for {pattern.concept}")
        if pattern.quiz_family:
            family = (families or {}).get(pattern.quiz_family)
            if family is None:
                raise CatalogError(f"{path}: unknown quiz family {pattern.quiz_family}")
            if family.pattern != pattern.id:
                raise CatalogError(f"{path}: quiz family {family.id} belongs to {family.pattern}")
        found[pattern.id] = pattern
    return found
