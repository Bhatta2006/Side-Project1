# The Socrat learning engine: how it fits together and how to extend it

For the owner and any engineer or agent extending the engine. The audit against the master prompt
is `docs/implementation/ule-gap-audit.md`; the progress log is
`docs/implementation/universal-engine-plan.md`; the operating manual is
`docs/implementation/HANDOFF.md`.

## How a request becomes a course

```
learner text ──► intent (coursegen/intent.py; model + rules fallback; engine/safety.py adds notes)
                 │  domain adapter chosen (engine/domains.py), stored on the brief
                 ▼
             diagnostic (coursegen/diagnostic.py; model writes, code scores, sets the start level)
                 ▼
             outline job (coursegen/jobs.py run_outline): architect → code checks (schema, catalog,
                 │  competency graph: outline.graph_issues) → critic → revise; assumptions logged
                 ▼
             learner inspects the blueprint on /new, publishes
                 ▼
             first slice queued at once (coursegen/prefetch.initial, from the diagnosed start),
             the rest kept 3 ahead of the learner (prefetch.request)
                 ▼
             package job per concept (jobs.run_package):
               search (coursegen/search.py, if providers set) → researcher (only real results)
               → strategist plan (engine/strategy.py, from engine/evidence_library.py)
               → author → gates (schema, math, physics, code runs, links, citations)
               → quiz/prompts/exercises/experiments/tasks → atoms → visuals (engine/design.py)
               → fact check + reviewer → validation report (coursegen/validation.py: five states)
               → release (catalog/generated.store_concept, version kept, job linked)
               transient failures retry with backoff, then "dead"; lifecycle shown on /new
                 ▼
             learner works: evidence (append-only) → mastery (mastery/model.py) and stages
             (mastery/evidence.py) → planner, coach proposals (adaptive/), reviews (learn/reviews.py)
                 ▼
             course evolves: bridge lessons on accepted proposals (coursegen/evolve.py), every
             change a visible revision; maintainer keeps links healthy (coursegen/maintain.py)
```

Models propose and write; code decides, checks and scores.

Kept stable across change:
- **Quiz ids across rewrites:** `catalog/revisions.carry` runs in `store_concept`. A rewritten
  question keeps its old id as a former id; a dropped one moves to `Concept.retired_quiz`, never
  offered but still found by `Concept.quiz_item` (always use it to look an item up by id).
- **Claims to sources:** `coursegen/research.ground` maps every inline `[n]` to its sentence,
  offset, source and passage (`Concept.citations`); weak overlap is a `grounding` warning.
- **Scoring policy:** `mastery.POLICY` is a digest of the scoring numbers; each learner state
  records it, and `mastery.replay` rebuilds a state from evidence under the current policy.
- **Module versions:** `catalog/revisions.module_version`, derived from the module and its
  concepts' content.
- **Outline reuse:** an identical brief (ignoring id and budgets) reuses a critic-passed
  outline with no model call (`jobs.reusable_outline`).
- **Result envelope:** `coursegen/roles.envelope` records each model call's parse result,
  confidence, assumptions and unresolved issues in the job log. Every model call records its model,
prompt version (a hash of the instructions), time and cost in the job log.

## Add a domain

1. Register an `Adapter` in `services/api/src/socrat/engine/domains.py`: keywords (whole words
   learners use, including school words), methods, activities, assessments, renderers it may use,
   harness capabilities that can verify answers, `verifiable` (`fully`, `partly`, `limited`),
   `needs_physical_practice`, `needs_external_evaluator`, fixed safety notes.
2. Add a representation line for it in `engine/strategy.py` `REPRESENTATION`.
3. If answers can be checked by code, add a harness capability (below) and list it.
4. Add an archetype request to `engine/benchmark.REQUESTS` if it is a new kind of subject.
5. Tests: `tests/test_engine_registry.py` (adapter checks) and a classification case in
   `tests/test_evaluation.py`.
Never claim verification you do not have: an adapter that is not `fully` verifiable makes every
lesson `human_review_required` until a named person confirms it.

## Add an activity type

1. Data: a typed model in `catalog/schema.py` on `Concept` (see `Task`), validated, with a rubric
   or an answer key and an evaluator. Add it to the `Concept.sequence` vocabulary, and, if it
   renders on the lesson page, to `apps/web/src/lib/sequence.ts` so the page orders it.
2. Generation: a prompt block in `coursegen/package.py` and parsing in `build_concept`; ask for it
   only where it fits (see `wants_tasks`).
3. Its assessment contract in `engine/assessments.describe` (format, evaluation, scoring,
   partial credit, alternates, feedback, assistance, evidence type).
4. Evidence: map its kind in `mastery/evidence.TYPE` and, if it writes evidence, a weight in
   `mastery/model.WEIGHTS`. Self-reports never count; a person's grade or a code check does.
5. Learner and owner views (`learn/views.py`, web component), tests.

## Add a renderer

1. A manifest in `engine/renderers.py` with typed params, events, runtime, evidence,
   accessible alternative, error handling; `sandboxed=True` if it runs in a frame.
2. A component in `apps/web/src/components/visuals/`, wired in
   `components/visualization-host.tsx`. Add it to `HEAVY` if it downloads a library.
3. List it in the adapters that may use it. The Experience Designer only offers renderers the
   adapter allows and that are not sandboxed.
4. Never run model-written code: specs are data the component interprets. Sketches and 3D films
   follow the same rule (`explainer/sketch.py`, `explainer/film.py`).
5. Tests: spec validation in `tests/test_engine_registry.py`, a browser test in
   `tests/e2e/visuals.spec.ts` (the dev gallery shows one of each).

## Add a harness capability

Typed input, a sandboxed run with a timeout and a uniform result, in `socrat/harness/`
(`registry.py`, `library.py`). Tutor tools, builder gates and grading all call the registry.

## Add or change a learning strategy

1. An entry in `engine/evidence_library.LIBRARY`: definition, outcomes, studied populations,
   strength, limits, when useful or unsuitable, Socrat's rule, how to measure it, references.
   Bump `VERSION`. Leave `REVIEWED_BY` empty until a qualified person has checked every entry.
2. A rule in `engine/strategy.plan` that picks it, with a reason a learner can read.
3. A measure in `engine/outcomes.py` if the rule needs one.
No learning styles: preferences change wording and format, never the method.

## Flags (all off by default) and how to switch them on

| Setting | What it turns on | Switch on | Roll back |
|---|---|---|---|
| `SOCRAT_LEARNING_REQUESTS_ENABLED` | Learner-made courses (`/new`) | after a live-model run of the benchmark | set false; existing courses stay readable |
| `SOCRAT_GEN_VISUALS` | Experience Designer adds lesson visuals | after reviewing a few designed lessons | set false; stored visuals still render |
| `SOCRAT_MAINTAINER_ENABLED` | Scheduled link checks and repairs | any time; no model | set false |
| `SOCRAT_RESEARCH_PROVIDERS` | Grounded research, e.g. `["wikipedia","arxiv","open-library"]` | after one live run | empty list |
| `SOCRAT_EXPLAINER_SKETCH_DECLARATIVE` | Sketches as data, no model code | after checking a few generated sketches | set false; old and new sketches both still play |
| `SOCRAT_LITE_MODE_ENABLED` | Data-use choice and lite mode | any time | set false |
| `SOCRAT_GEN_INITIAL_ON_PUBLISH` | Admin-published courses write their first slice at once | any time | set false |
| `SOCRAT_WORKER_RUNS_GENERATION` | Generation in the worker | see `docs/operations/api-worker-split.md` | as there |

Migrations 0034 to 0044 are additive; each has a tested downgrade
(`tests/test_quiz_runtime_tables.py`). If `main` gains migrations, renumber `down_revision` and
`schema_revision.py` at merge time.

## What still needs people

- A live-model run of every role and of `scripts/dev/benchmark.py` (needs a key).
- Qualified reviewers for a sample of generated courses (`benchmark.HUMAN_REVIEW`) and for the
  Learning Evidence Library.
- Named people to confirm lessons marked `human_review_required` and to grade performance tasks.
