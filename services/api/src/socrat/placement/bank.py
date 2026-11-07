"""The placement bank: hard, placement-only questions per concept.

``content/placement/<course>.yaml`` lists, per concept, questions written to be the hardest
of their topic: edge cases, special cases, traces, fill-in-the-blank and find-the-bug. They are
never shown in lessons or practice, so a learner cannot have seen them before placement.

    course: zero
    concepts:
      lists:                # local id, or qualified "dsa:arrays-hashing"
        - id: alias-append
          kind: output      # mcq | output | bug | fill
          prompt: ...
          options: [...]    # authored correct answer first is fine; display order is shuffled
          answer: 0
          explanation: ...
          difficulty: 5     # placement items are 4 or 5
          languages: [python]   # only when the question uses one language's syntax
"""

from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pydantic import Field, ValidationError

from socrat.catalog.schema import Model, QuizItem, Slug

if TYPE_CHECKING:
    from socrat.catalog.registry import Catalog

MIN_DIFFICULTY = 4
MAX_PER_CONCEPT = 10


class BankFile(Model):
    course: Slug
    concepts: dict[str, list[QuizItem]] = Field(default_factory=dict)


def load(folder: Path, catalog: "Catalog") -> dict[str, list[QuizItem]]:
    """Qualified concept -> its placement items. A missing folder means no bank."""
    items: dict[str, list[QuizItem]] = {}
    if not folder.is_dir():
        return items
    for path in sorted(folder.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        try:
            data = BankFile.model_validate(raw)
        except ValidationError as exc:
            raise ValueError(f"{path.name}: {exc}") from exc
        if data.course not in catalog.courses:
            raise ValueError(f"{path.name}: unknown course {data.course}")
        for key, questions in data.concepts.items():
            qualified = key if ":" in key else f"{data.course}:{key}"
            if qualified not in catalog.concepts:
                raise ValueError(f"{path.name}: unknown concept {qualified}")
            existing = items.setdefault(qualified, [])
            taken = {q.id for q in catalog.concepts[qualified].quiz} | {
                q.id for q in catalog.concepts[qualified].retired_quiz
            }
            for q in questions:
                if q.difficulty < MIN_DIFFICULTY:
                    raise ValueError(f"{qualified}/{q.id}: placement items are difficulty 4 or 5")
                if q.id in taken or any(x.id == q.id for x in existing):
                    raise ValueError(f"{qualified}/{q.id}: duplicate quiz item id")
                existing.append(q)
            if len(existing) > MAX_PER_CONCEPT:
                raise ValueError(f"{qualified}: at most {MAX_PER_CONCEPT} placement items")
    return items
