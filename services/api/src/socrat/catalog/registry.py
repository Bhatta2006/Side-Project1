"""Load, validate and index course packs.

Every concept is addressed globally as ``course:concept``. Prerequisites written
without a prefix belong to the same course.
"""

import hashlib
import json
import os
from dataclasses import dataclass, field
from functools import cache
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

import yaml

from socrat.catalog.atoms import AtomPack, PatternAtomPack
from socrat.catalog.patterns import Pattern
from socrat.catalog.projects import Project
from socrat.catalog.quizbank import QuizFamily
from socrat.catalog.schema import Concept, Course, Problem, TestCase

REPO_ROOT = Path(__file__).resolve().parents[5]
CONTENT_ROOT = REPO_ROOT / "content" / "courses"
# Generated hidden tests (deterministic, large) are build artifacts, not source files.
TESTS_ROOT = Path(os.environ.get("SOCRAT_CONTENT_TESTS", REPO_ROOT / ".cache" / "content-tests"))


class CatalogError(ValueError):
    pass


def qualify(course_id: str, ref: str) -> str:
    return ref if ":" in ref else f"{course_id}:{ref}"


def _read(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise CatalogError(f"{path}: expected a mapping")
    return value


def load_course(
    folder: Path, tests_root: Path | None = TESTS_ROOT, include_drafts: bool = False
) -> Course:
    """Draft concepts are validated here but left out unless ``include_drafts``: learners,
    placement and planning only ever see live concepts."""
    payload = _read(folder / "course.yaml")
    payload["concepts"] = [_read(p) for p in sorted((folder / "concepts").glob("*.yaml"))]
    problems = []
    for path in sorted((folder / "problems").glob("*.yaml")):
        problem = _read(path)
        if problem.get("id") != path.stem:
            raise CatalogError(f"{path}: file name must match problem id")
        built = tests_root / f"{problem['id']}.json" if tests_root else None
        if built is not None:
            if not built.exists():
                raise CatalogError(
                    f"missing tests for {problem['id']}: run python scripts/content/build.py"
                )
            problem["tests"] = json.loads(built.read_text(encoding="utf-8"))
        problems.append(problem)
    payload["problems"] = problems
    try:
        course = Course.model_validate(payload)
    except ValueError as exc:
        raise CatalogError(f"{folder.name}: {exc}") from exc
    drafts = {c.id for c in course.concepts if c.status == "draft"}
    if include_drafts or not drafts:
        return course
    modules = [
        m.model_copy(update={"concepts": [c for c in m.concepts if c not in drafts]})
        for m in course.modules
    ]
    return course.model_copy(
        update={
            "concepts": [c for c in course.concepts if c.id not in drafts],
            "modules": [m for m in modules if m.concepts],
        }
    )


@dataclass
class Catalog:
    courses: dict[str, Course]
    digest: str
    concepts: dict[str, Concept] = field(default_factory=dict)
    owner: dict[str, str] = field(default_factory=dict)  # qualified concept → course id
    prerequisites: dict[str, list[str]] = field(default_factory=dict)
    problems: dict[str, tuple[str, Problem]] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)  # global topological order
    atom_packs: dict[str, AtomPack] = field(default_factory=dict)
    patterns: dict[str, "Pattern"] = field(default_factory=dict)
    quiz_families: dict[str, "QuizFamily"] = field(default_factory=dict)
    projects: dict[str, "Project"] = field(default_factory=dict)
    pattern_atoms: dict[str, PatternAtomPack] = field(default_factory=dict)
    quiz_root: Path | None = None  # content/quiz: families, generators, verified manifest
    misconceptions: set[str] = field(default_factory=set)  # controlled misconception IDs

    def course(self, course_id: str) -> Course:
        try:
            return self.courses[course_id]
        except KeyError as exc:
            raise CatalogError(f"unknown course {course_id}") from exc

    def concept(self, qualified: str) -> Concept:
        return self.concepts[qualified]

    def problem(self, problem_id: str) -> Problem:
        return self.problems[problem_id][1]

    def closure(self, targets: list[str]) -> list[str]:
        """Targets plus every transitive prerequisite, in topological order."""
        needed: set[str] = set()
        stack = list(targets)
        while stack:
            node = stack.pop()
            if node not in needed:
                needed.add(node)
                stack.extend(self.prerequisites[node])
        return [node for node in self.order if node in needed]

    def course_concepts(self, course_id: str) -> list[str]:
        course = self.course(course_id)
        return [f"{course.id}:{cid}" for module in course.modules for cid in module.concepts]

    def module_of(self, qualified: str) -> str:
        course = self.course(self.owner[qualified])
        local = qualified.split(":", 1)[1]
        return next(m.id for m in course.modules if local in m.concepts)

    def public_tests(self, problem_id: str) -> list[TestCase]:
        return [test for test in self.problem(problem_id).tests if test.public]


def build(courses: list[Course]) -> Catalog:
    ids = [c.id for c in courses]
    if len(set(ids)) != len(ids):
        raise CatalogError("duplicate course id")
    payload = json.dumps([c.model_dump(mode="json") for c in courses], sort_keys=True)
    catalog = Catalog({c.id: c for c in courses}, hashlib.sha256(payload.encode()).hexdigest())
    for course in courses:
        local_ids = [c.id for c in course.concepts]
        if len(set(local_ids)) != len(local_ids):
            raise CatalogError(f"{course.id}: duplicate concept id")
        module_members = [cid for m in course.modules for cid in m.concepts]
        if sorted(module_members) != sorted(local_ids):
            raise CatalogError(f"{course.id}: every concept must belong to exactly one module")
        for concept in course.concepts:
            if concept.module not in {m.id for m in course.modules if concept.id in m.concepts}:
                raise CatalogError(f"{course.id}:{concept.id}: module mismatch")
            key = f"{course.id}:{concept.id}"
            catalog.concepts[key] = concept
            catalog.owner[key] = course.id
            catalog.prerequisites[key] = [qualify(course.id, p) for p in concept.prerequisites]
        for problem in course.problems:
            if problem.id in catalog.problems:
                raise CatalogError(f"duplicate problem id {problem.id}")
            catalog.problems[problem.id] = (course.id, problem)
            for cid in problem.concepts:
                if cid not in local_ids:
                    raise CatalogError(f"problem {problem.id}: unknown concept {cid}")
        for level in course.levels:
            if level.start_concept and level.start_concept not in local_ids:
                raise CatalogError(f"{course.id}: level {level.id} starts at unknown concept")
    for key, prerequisites in catalog.prerequisites.items():
        for prerequisite in prerequisites:
            if prerequisite not in catalog.concepts:
                raise CatalogError(f"{key}: unknown prerequisite {prerequisite}")
    for course in courses:
        for concept in course.concepts:
            for problem_id in concept.problems:
                owner = catalog.problems.get(problem_id)
                if owner is None or owner[0] != course.id:
                    raise CatalogError(f"{course.id}:{concept.id}: unknown problem {problem_id}")
    try:
        sorter = TopologicalSorter(catalog.prerequisites)
        # Stable order: ready nodes sorted by course order then authoring order.
        position = {key: index for index, key in enumerate(catalog.concepts)}
        sorter.prepare()
        while sorter.is_active():
            ready = sorted(sorter.get_ready(), key=position.__getitem__)
            catalog.order.extend(ready)
            sorter.done(*ready)
    except CycleError as exc:
        raise CatalogError(f"prerequisite cycle: {exc.args[1]}") from exc
    return catalog


def load(root: Path = CONTENT_ROOT, tests_root: Path | None = TESTS_ROOT) -> Catalog:
    """tests_root=None loads authoring data only (used while building tests)."""
    folders = sorted(p for p in root.iterdir() if (p / "course.yaml").exists())
    from socrat.catalog import atoms

    catalog = build([load_course(folder, tests_root) for folder in folders])
    # Drafts must still fit the graph: known prerequisites, one module each, no cycles.
    # A live concept that needs a draft fails the build above as an unknown prerequisite.
    build([load_course(folder, None, include_drafts=True) for folder in folders])
    try:
        catalog.atom_packs = atoms.load(root.parent / "atoms", catalog.concepts, catalog.courses)
        catalog.pattern_atoms = atoms.load_pattern_packs(
            root.parent / "atoms", catalog.concepts, catalog.courses
        )
    except (ValueError, OSError, yaml.YAMLError) as exc:
        raise CatalogError(f"Invalid atom catalogue: {exc}") from exc
    from socrat.catalog import patterns, projects, quizbank

    taxonomy = atoms.load_taxonomy(root.parent / "atoms")
    catalog.misconceptions = taxonomy
    catalog.quiz_root = root.parent / "quiz"
    catalog.quiz_families = quizbank.load(catalog.quiz_root, catalog, taxonomy)
    catalog.patterns = patterns.load(
        root.parent / "patterns",
        catalog,
        taxonomy,
        lambda: patterns.external_problem_ids(root.parent / "practice" / "problems.jsonl"),
        catalog.quiz_families,
    )
    quizbank.check_patterns(catalog.quiz_families, catalog.patterns)
    catalog.projects = projects.load(root.parent / "projects", catalog)
    registry_file = root.parent / "sources" / "registry.yaml"
    if registry_file.exists():
        from socrat.catalog import sources

        try:
            registry = sources.load_registry(registry_file)
        except (ValueError, OSError, yaml.YAMLError) as exc:
            raise CatalogError(f"Invalid source registry: {exc}") from exc
        sources.check_catalog(catalog, registry)
    catalog.digest = hashlib.sha256(
        json.dumps(
            {
                "catalog": catalog.digest,
                "atoms": {q: p.model_dump(mode="json") for q, p in catalog.atom_packs.items()},
            }
            | (
                {"patterns": {k: v.model_dump(mode="json") for k, v in catalog.patterns.items()}}
                if catalog.patterns
                else {}
            )
            | (
                {"quiz": {k: v.model_dump(mode="json") for k, v in catalog.quiz_families.items()}}
                if catalog.quiz_families
                else {}
            )
            | (
                {
                    "pattern_atoms": {
                        k: v.model_dump(mode="json") for k, v in catalog.pattern_atoms.items()
                    }
                }
                if catalog.pattern_atoms
                else {}
            )
            | (
                {"projects": {k: v.model_dump(mode="json") for k, v in catalog.projects.items()}}
                if catalog.projects
                else {}
            ),
            sort_keys=True,
        ).encode()
    ).hexdigest()
    return catalog


@cache
def default_catalog() -> Catalog:
    return load(Path(os.environ.get("SOCRAT_CONTENT_ROOT", CONTENT_ROOT)))
