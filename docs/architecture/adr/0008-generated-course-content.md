# ADR-0008: AI may generate course content as data, under deterministic gates

- **Status:** Proposed
- **Date:** 2026-10-24
- **Decision owners:** Product, Engineering, Learning Design
- **Amends:** ADR-0002 (the clause "AI cannot freely generate a curriculum")
- **Design:** [course-generation.md](../course-generation.md)

## Context

Every course so far is hand-authored YAML in `content/courses`. Adding a new skill (ML
engineering, AI basics) means writing its whole curriculum by hand, which does not scale.
ADR-0002 kept AI away from the curriculum so that eligibility, mastery and assessment stay
reproducible. That reason still holds for decisions. It does not require that a human
types the content those decisions run over.

## Decision

- Agents may generate course outlines and concept content. Their output is **data** in the
  existing content schemas (`Course`, `Concept`, atoms, quiz items, problems), stored in
  versioned database rows next to the file packs.
- Deterministic services still own eligibility, prerequisites, placement, mastery,
  planning, assessment scoring and every state write. Agents return JSON. Validated,
  deterministic code stores it. No model identity gets database credentials.
- A concept can be `planned`: present in the graph and on the roadmap, with its lesson and
  activities held until its content is released. Learners never see unreleased content.
- Release requires the deterministic gates (schema, graph, executable checks in the
  isolated execution plane, originality) and then an independent reviewer pass. Released
  content is immutable and versioned (ADR-0003). It can be quarantined.
- Content-standard principle 4 becomes: "AI may draft; only the gates release."
- Hand-authored packs (DSA, CP, Zero) stay the gold standard and the review bar.

## Consequences

- New courses cost model time instead of author time. Quality depends on the gates and
  the reviewer, and is measured against the gold packs before launch.
- An invalid generated course must never break hand-authored ones. The merged catalog
  falls back to the file packs and logs the error.
- Mastery replay (ADR-0004) still works, because content is versioned and decisions remain
  deterministic.

## Verification

- A database-stored course with planned concepts enrolls, plans and places learners. Its
  planned lessons return `423 concept_preparing`.
- Corrupting a stored course leaves every file course serving.
- With all model access disabled, every released course remains fully usable.
