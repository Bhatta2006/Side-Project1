"""Domain adapters: what the engine knows about teaching and checking each kind of subject.

An adapter is data, not a special case in the compiler. It says how to recognise the subject,
which teaching methods and activities suit it, how it can be assessed, which renderers and
harness capabilities apply, what is unsafe, and above all how much the engine can honestly
verify. A text-only tutor cannot validate a physical skill; the adapter states that so the
course and the interface say it too.

Adding a domain: add an ``Adapter`` below (or register one at start-up). Keywords only
classify; unknown subjects fall back to ``general`` rather than being forced into a template.
"""

import re
from dataclasses import dataclass
from typing import Literal

Verifiable = Literal["fully", "partly", "limited"]


@dataclass(frozen=True)
class Adapter:
    id: str
    name: str
    keywords: tuple[str, ...]  # whole-word hints; classification only
    methods: tuple[str, ...]  # learning-science techniques that suit it (see plan section 8)
    activities: tuple[str, ...]
    assessments: tuple[str, ...]
    renderers: tuple[str, ...]  # renderer ids from engine.renderers
    capabilities: tuple[str, ...]  # harness capability names that can verify answers
    verifiable: Verifiable
    needs_physical_practice: bool = False
    needs_external_evaluator: bool = False
    safety: tuple[str, ...] = ()  # fixed requirements added to every course in the domain
    terminology: tuple[str, ...] = ()  # terms kept in English in translated content


ADAPTERS: dict[str, Adapter] = {}


def register(adapter: Adapter) -> Adapter:
    if adapter.id in ADAPTERS:
        raise ValueError(f"domain adapter {adapter.id} is already registered")
    ADAPTERS[adapter.id] = adapter
    return adapter


register(
    Adapter(
        id="math-science",
        name="Mathematics and sciences",
        keywords=(
            "math",
            "maths",
            "mathematics",
            "algebra",
            "calculus",
            "geometry",
            "statistics",
            "probability",
            "physics",
            "chemistry",
            "biology",
            "science",
            "quantum",
            "mechanics",
            "trigonometry",
            "equations",
        ),
        methods=(
            "worked-examples",
            "self-explanation",
            "retrieval-practice",
            "interleaving",
            "transfer",
        ),
        activities=(
            "explanation",
            "worked-example",
            "interactive-graph",
            "simulation",
            "problem-set",
            "derivation",
        ),
        assessments=("numeric-check", "symbolic-equivalence", "step-check", "explain"),
        renderers=("markdown", "function-plot", "simulation", "concept-map", "concept-playground"),
        capabilities=("math.check", "physics.simulate"),
        verifiable="fully",
        safety=("Lab procedures are simulated; hazardous experiments need qualified supervision.",),
    )
)
register(
    Adapter(
        id="software",
        name="Software and computer science",
        keywords=(
            "programming",
            "coding",
            "code",
            "software",
            "algorithm",
            "algorithms",
            "python",
            "java",
            "c++",
            "cpp",
            "javascript",
            "data structures",
            "dsa",
            "competitive",
            "web development",
            "database",
            "sql",
            "machine learning",
            "ai",
        ),
        methods=(
            "worked-examples",
            "retrieval-practice",
            "interleaving",
            "deliberate-practice",
            "transfer",
        ),
        activities=(
            "explanation",
            "worked-example",
            "code-lab",
            "debugging",
            "project",
            "algorithm-visualiser",
        ),
        assessments=("automated-tests", "code-review-rubric", "explain", "project-rubric"),
        renderers=("markdown", "code-studio", "concept-map", "concept-playground"),
        capabilities=("code.judge",),
        verifiable="fully",
        safety=("Code runs only in the isolated execution sandbox.",),
    )
)
register(
    Adapter(
        id="electronics",
        name="Electrical and electronics engineering",
        keywords=(
            "electronics",
            "electrical",
            "circuit",
            "circuits",
            "voltage",
            "arduino",
            "signal",
            "signals",
            "transistor",
            "semiconductor",
            "embedded",
            "power systems",
        ),
        methods=(
            "worked-examples",
            "predict-observe-explain",
            "concrete-to-abstract",
            "retrieval-practice",
        ),
        activities=(
            "explanation",
            "circuit-simulation",
            "dimensional-check",
            "virtual-experiment",
            "problem-set",
        ),
        assessments=("numeric-check", "dimensional-analysis", "explain"),
        renderers=("markdown", "simulation", "function-plot", "self-check"),
        capabilities=("math.check", "physics.simulate"),
        verifiable="partly",
        needs_physical_practice=True,
        safety=(
            "No instructions for mains or high-voltage work; use simulations.",
            "Real hardware experiments need low voltage and qualified supervision.",
        ),
    )
)
register(
    Adapter(
        id="music",
        name="Music and sound",
        keywords=(
            "music",
            "guitar",
            "piano",
            "violin",
            "drums",
            "singing",
            "vocals",
            "raga",
            "ragas",
            "carnatic",
            "hindustani",
            "melody",
            "rhythm",
            "harmony",
            "composition",
            "instrument",
        ),
        methods=("deliberate-practice", "spaced-practice", "dual-coding", "concrete-to-abstract"),
        activities=(
            "listening",
            "theory-explanation",
            "rhythm-exercise",
            "composition",
            "practice-routine",
        ),
        assessments=("theory-quiz", "self-check", "recording-rubric"),
        renderers=("markdown", "timeline", "self-check"),
        capabilities=(),
        verifiable="limited",
        needs_physical_practice=True,
        needs_external_evaluator=True,
        safety=("Protect hearing: keep volume moderate and take breaks.",),
    )
)
register(
    Adapter(
        id="animation-movement",
        name="Animation, film and movement",
        keywords=(
            "animation",
            "animator",
            "filmmaking",
            "film",
            "video editing",
            "dance",
            "movement",
            "choreography",
            "drawing",
            "illustration",
            "storyboard",
            "cinematography",
            "yoga",
            "sport",
            "fitness",
            "martial",
        ),
        methods=("deliberate-practice", "worked-examples", "dual-coding", "feedback"),
        activities=("demonstration", "timeline-exercise", "critique", "assignment", "portfolio"),
        assessments=("self-check", "portfolio-rubric", "peer-or-expert-review"),
        renderers=("markdown", "timeline", "self-check", "concept-map"),
        capabilities=(),
        verifiable="limited",
        needs_physical_practice=True,
        needs_external_evaluator=True,
        safety=("Physical practice: warm up, stay within your limits, stop if you feel pain.",),
    )
)
register(
    Adapter(
        id="general",
        name="General subjects",
        keywords=(),
        methods=(
            "retrieval-practice",
            "spaced-practice",
            "elaborative-questioning",
            "worked-examples",
        ),
        activities=("explanation", "reading", "reflection", "project"),
        assessments=("quiz", "explain", "project-rubric"),
        renderers=("markdown", "concept-map", "concept-playground", "self-check"),
        capabilities=(),
        verifiable="partly",
        safety=(
            "For health, legal or financial topics this is education, not professional advice.",
        ),
    )
)


def classify(text: str, hint: str = "") -> Adapter:
    """The best-matching adapter for a subject. ``hint`` (a domain name from the intent parser)
    counts double. Ties and no match go to ``general``."""
    scores: dict[str, int] = {}
    for source, weight in ((text.lower(), 1), (hint.lower(), 2)):
        for adapter in ADAPTERS.values():
            for word in adapter.keywords:
                if re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", source):
                    scores[adapter.id] = scores.get(adapter.id, 0) + weight
    if hint.lower() in ADAPTERS and hint.lower() != "general":  # "general" is a default, not a vote
        scores[hint.lower()] = scores.get(hint.lower(), 0) + 3
    if not scores:
        return ADAPTERS["general"]
    best = max(scores.values())
    top = sorted(a for a, s in scores.items() if s == best)
    return ADAPTERS[top[0]] if len(top) == 1 else ADAPTERS["general"]


VERIFIABLE_RANK = {"fully": 2, "partly": 1, "limited": 0}


def check_adapter_renderers() -> list[str]:
    """Problems if an adapter names a renderer or capability that does not exist."""
    from socrat.engine import renderers
    from socrat.harness import registry as harness

    known = renderers.all_manifests()
    caps = set(harness.capabilities()) | {"code.judge"}  # the judge is wired in, see harness doc
    problems = []
    for a in ADAPTERS.values():
        problems += [f"{a.id}: unknown renderer {r}" for r in a.renderers if r not in known]
        problems += [f"{a.id}: unknown capability {c}" for c in a.capabilities if c not in caps]
    return problems
