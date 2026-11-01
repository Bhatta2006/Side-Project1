"""Versioned, bounded teaching atoms. Answer keys never belong in learner views."""

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, model_validator

from socrat.catalog.schema import Language, Model, Provenance, Review, Slug

AtomKind = Literal[
    "hook",
    "concept",
    "worked",
    "faded",
    "visualizer",
    "trace",
    "predict",
    "debug",
    "micro",
    "pattern",
    "explanation",
    "reflection",
    "classify",  # "which pattern?" drill over a few problem statements
]


class Adapter(Model):
    code: str = Field(min_length=1, max_length=4000)
    stdin: str = Field(default="", max_length=2000)
    expected: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def bounded(self):
        if len(self.code.splitlines()) > 25:
            raise ValueError("an atom adapter has at most 25 lines")
        return self


class Step(Model):
    state: str = Field(min_length=1, max_length=2000)
    prompt: str = Field(min_length=5, max_length=600)
    options: list[str] = Field(min_length=2, max_length=6)
    answer: int = Field(ge=0)
    explanation: str = Field(min_length=5, max_length=1000)

    @model_validator(mode="after")
    def valid_answer(self):
        if self.answer >= len(self.options) or len(set(self.options)) != len(self.options):
            raise ValueError("a check needs distinct options and a valid answer")
        return self


class Atom(Model):
    id: Slug
    kind: AtomKind
    title: str = Field(min_length=2, max_length=120)
    objective: str = Field(min_length=5, max_length=300)
    body: str = Field(default="", max_length=2500)
    why: str = Field(default="", max_length=1200)
    seconds: int = Field(ge=10, le=120)
    adapters: dict[Language, Adapter] = Field(default_factory=dict)
    steps: list[Step] = Field(default_factory=list, max_length=12)
    misconception: Slug | None = None
    # Distinct solution structures let the session composer avoid near-identical practice.
    followup: Slug | None = None

    @model_validator(mode="after")
    def learning_contract(self):
        if not self.body.strip():
            raise ValueError("an atom needs a learner-facing body")
        limit = 80 if self.kind == "pattern" else 120
        if len(re.findall(r"\S+", self.body)) > limit:
            raise ValueError(f"{self.kind} body exceeds {limit} words")
        if self.kind == "hook" and len(re.findall(r"[.!?](?:\s|$)", self.body)) > 2:
            raise ValueError("a hook has at most two sentences")
        if (
            self.kind
            in {"faded", "visualizer", "trace", "predict", "debug", "explanation", "classify"}
            and not self.steps
        ):
            raise ValueError("interactive atoms require authored checks")
        if self.kind == "micro" and not self.misconception:
            raise ValueError("micro-lessons need a controlled misconception")
        for adapter in self.adapters.values():
            limit = 10 if self.kind == "predict" else 15 if self.kind in {"trace", "debug"} else 25
            if len(adapter.code.splitlines()) > limit:
                raise ValueError(f"{self.kind} code exceeds {limit} lines")
        return self


class AtomPack(Model):
    concept: str = Field(pattern=r"^[a-z][a-z0-9-]*:[a-z][a-z0-9-]*$")
    concept_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    owner: str = Field(min_length=2, max_length=120)
    rights: str = Field(min_length=5, max_length=300)
    changelog: str = Field(min_length=5, max_length=1000)
    rollback: str = Field(min_length=3, max_length=160)
    status: Literal["draft", "released", "quarantined"] = "draft"
    review: Review | None = None
    # Pack-level provenance keeps learner-facing atom JSON unchanged.
    provenance: Provenance | None = None
    atoms: list[Atom] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def publication(self):
        # A person, or for generated packs the release gates (ADR-0008), signs the release.
        if self.status == "released" and self.review is None:
            raise ValueError("release requires a review record")
        if self.status == "released" and any(
            adapter.expected is None for atom in self.atoms for adapter in atom.adapters.values()
        ):
            raise ValueError("released adapters need reviewed expected output")
        if len({a.id for a in self.atoms}) != len(self.atoms):
            raise ValueError("duplicate atom id")
        return self


class PatternAtomPack(AtomPack):
    """Atoms for one pattern: ``content/atoms/<course>/<concept>/<pattern>.yaml``.

    Kept apart from the concept's released pack so new, unreviewed atoms never appear under
    that pack's review record. The session composer does not read these packs.
    """

    pattern: str = Field(pattern=r"^[a-z][a-z0-9-]*:[a-z][a-z0-9-]*/[a-z][a-z0-9-]*$")

    @model_validator(mode="after")
    def belongs_to_concept(self):
        if not self.pattern.startswith(self.concept + "/"):
            raise ValueError(f"pattern {self.pattern} is not in concept {self.concept}")
        return self


def load_taxonomy(root: Path) -> set[str]:
    """The controlled misconception IDs (``misconceptions.yaml`` next to the atom packs)."""
    taxonomy_file = root / "misconceptions.yaml"
    if not taxonomy_file.exists():
        return set()
    return set(yaml.safe_load(taxonomy_file.read_text(encoding="utf-8")) or [])


def load(root: Path, concepts: dict, courses: dict) -> dict[str, AtomPack]:
    packs = {}
    taxonomy = load_taxonomy(root)
    for path in sorted(root.glob("*/*.yaml")):
        pack = AtomPack.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        if pack.concept not in concepts or pack.concept in packs:
            raise ValueError(f"{path}: unknown or duplicate concept")
        if pack.concept_version != courses[pack.concept.split(":")[0]].version:
            raise ValueError(f"{path}: stale concept version")
        for atom in pack.atoms:
            if atom.misconception and atom.misconception not in taxonomy:
                raise ValueError(f"{path}: unknown misconception {atom.misconception}")
        packs[pack.concept] = pack
    return packs


def load_pattern_packs(root: Path, concepts: dict, courses: dict) -> dict[str, PatternAtomPack]:
    """Pattern packs keyed by pattern id; the file path must match the pattern."""
    packs: dict[str, PatternAtomPack] = {}
    taxonomy = load_taxonomy(root)
    for path in sorted(root.glob("*/*/*.yaml")):
        pack = PatternAtomPack.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        course, concept, slug = path.relative_to(root).with_suffix("").parts
        if pack.pattern != f"{course}:{concept}/{slug}" or pack.pattern in packs:
            raise ValueError(f"{path}: file path must match pattern {pack.pattern}")
        if pack.concept not in concepts:
            raise ValueError(f"{path}: unknown concept {pack.concept}")
        if pack.concept_version != courses[course].version:
            raise ValueError(f"{path}: stale concept version")
        for atom in pack.atoms:
            if atom.misconception and atom.misconception not in taxonomy:
                raise ValueError(f"{path}: unknown misconception {atom.misconception}")
        packs[pack.pattern] = pack
    return packs
