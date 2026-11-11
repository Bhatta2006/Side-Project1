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
- **Imprecise facts get one polish round:** a package that passes but carries fact claims the
  checker called *imprecise* is revised once (only with under half the lesson's budget spent).
  If that round fails, the first passing version is released as it was (`jobs.run_package`).
- **Researcher sources by subject:** only software courses see the whole source registry; other
  adapters see `research.GENERAL_SOURCES`.
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

## What blocks a lesson from release

A lesson is held back by a **defect**, not by a score. Blocking: a deterministic gate that fails
(schema, length, code, math, links), a fact-check claim marked `incorrect`, a missing fact check,
or a review that could not be read. The reviewer's 1 to 5 scores are a signal, and a cheap
reviewer is noisy, so a score under target (5 for correctness, 4 for the other dimensions) is
stored as a **warning** and the lesson is released as `pass_with_warnings`. Only a score below
`SOCRAT_GEN_SCORE_FLOOR` (default 3, range 2 to 5) blocks. Raise the floor as stronger author and
reviewer models are put in place. Released lessons stay labelled AI-generated and not reviewed by
a person; warnings are visible to the owner in the Upkeep tab. A passing score is a same-class
model finding nothing blocking, not proof of correctness.

A model reply cut off at its token limit is asked again once with a doubled budget (ceiling
16000) before it is counted, so a reasoning model that spends its budget thinking does not cost a
whole revision round.

## Flags (all off by default) and how to switch them on

| Setting | What it turns on | Switch on | Roll back |
|---|---|---|---|
| `SOCRAT_LEARNING_REQUESTS_ENABLED` | Learner-made courses (`/new`) | after a live-model run of the benchmark | set false; existing courses stay readable |
| `SOCRAT_GEN_VISUALS` | Experience Designer adds lesson visuals | after reviewing a few designed lessons | set false; stored visuals still render |
| `SOCRAT_MAINTAINER_ENABLED` | Scheduled link checks and repairs | any time; no model | set false |
| `SOCRAT_RESEARCH_PROVIDERS` | Grounded research. Keyless: `wikipedia`, `wikibooks`, `wikiversity`, `mit-ocw`, `openstax`, `arxiv`, `openalex`, `open-library`. Keyed: `web`, `youtube` | after one live run | empty list |
| `SOCRAT_WEB_SEARCH_API_KEY` | Brave Search API key for the `web` provider (articles and the wider web); `web` adds nothing without it | with `web` | empty |
| `SOCRAT_OPENALEX_API_KEY` | Optional key for `openalex` (it works without one on a small shared allowance) | when papers matter | empty |
| `SOCRAT_RESEARCH_READ_PAGES` | Read the chosen pages (public https, robots.txt honoured, 6,000 characters each, 3 per lesson) and write from their text instead of the search snippet. On by default; only acts when providers are set | on | set false |
| `SOCRAT_YOUTUBE_API_KEY` | YouTube Data API v3 key for the `youtube` provider (about 100 lessons a day on the free quota) | with `youtube` | empty |
| `SOCRAT_YOUTUBE_TRANSCRIPTS` | Video captions as the author's source text (reads the public watch page; no official API) | owner decision | false |
| `SOCRAT_EXPLAINER_SKETCH_DECLARATIVE` | Sketches as data, no model code | after checking a few generated sketches | set false; old and new sketches both still play |
| `SOCRAT_LITE_MODE_ENABLED` | Data-use choice and lite mode | any time | set false |
| `SOCRAT_GEN_MARKED_ANSWERS` | Quiz and atom writers mark the right option instead of giving its index (`coursegen/keyed.py`; replies in either form are always parsed) | at the next live run, comparing fact-checker `incorrect` quiz claims off and on | set false |
| `SOCRAT_GEN_APPLIED_LESSONS` | Learner courses end each module with a planned "Apply" lesson (`coursegen/applied.py`) | after reading a few generated ones | set false; existing ones stay as planned lessons |
| `SOCRAT_GEN_INITIAL_ON_PUBLISH` | Admin-published courses write their first slice at once | any time | set false |
| `SOCRAT_GEN_TIERS` | Model tiers per agent role (`coursegen/roles.ROLE_TIER`): `strong` for architect, reviser, facts, reviewer; `fast` for intent, stylist, researcher, experience; the default model for the rest. A garbled quiz or atoms reply, and a part on its last round, is asked of the strong model. A role's entry in `SOCRAT_GEN_ROLES` wins over its tier | after a live run that compares cost per released lesson | empty: one model for all |
| `SOCRAT_GEN_LESSON_COST_TARGET_USD` | Marks courses above this cost per released lesson in `GET /admin/engine-costs` (default 0.10). Stops nothing | any time | 0 |
| `SOCRAT_GEN_FAST_FIRST_LESSON` | A learner's first lesson takes the search's best-ranked sources as they are, without the researcher's model call. Links are still checked | any time | false |
| `SOCRAT_GEN_FIRST_LESSON_PREVIEW` | The owner of a private course may read their first lesson's draft once it passes the lesson gates, labelled as still being checked. Read-only. Never with safety notes or a learner under 13 | any time | false |
| `SOCRAT_PRACTICE_BANK` | Practice sets are built from the lesson's own checked material (in-lesson checks, section rows) when it holds at least 3 questions: no model call, not counted against the daily allowance. Otherwise a model writes the set | any time | false |
| `SOCRAT_PRACTICE_EVIDENCE` | Answers to bank questions count as recall evidence: at most 3 per lesson a day, each question once a day. Model-written sets never count | any time | false |
| `SOCRAT_LESSON_SIGNALS` | The app reports how each lesson is read (furthest page, "simpler" and "deeper" taps, rereads, questions). Counters only, never evidence. The stuck detector reads them as weak signals, the tutor is told them, and the learner reads them at `GET /api/v1/memory` | any time | false |
| `SOCRAT_EXPLAINER_SECTION_VISUALS` | Each page of a lesson offers "Show me this part": a shared visual built from that page's own text, made once and reused by every learner, not charged to anyone's plan | any time | false |
| `SOCRAT_GEN_BUDGET_PER_LESSON_USD` | Each released lesson adds this much to what its course may spend, so a long course that keeps releasing never stops itself; one that spends without releasing still pauses. 0 keeps the fixed course budget | any time | 0 |
| `SOCRAT_GEN_LESSONS_PER_DAY` | Lessons written for one course in any 24 hours. A lesson over the quota is queued with the time it will be written and the learner is told when. 0 is no quota | restart | 0 |
| `SOCRAT_GEN_INITIAL_LESSONS` | Lessons written when a course is published, before the learner has read a line (1 to 6) | restart | 6 |
| `SOCRAT_GEN_LESSONS_AHEAD` | Lessons kept written ahead of the learner, counting the one they are on (1 to 5) | restart | 3 |
| `SOCRAT_REQUEST_MATCHING` | Match before build: a new request is compared with the courses the learner may already take (their own, and ones other learners chose to share) and a fit is offered to start at once. Private courses are never compared; no model is called | any time | false |
| `SOCRAT_PLAYGROUND_FREE_PER_WEEK` | Visuals a learner on the free plan may ask for in the Playground each week (0 to 20). Shared lesson visuals are free already | restart | 0 |
| `SOCRAT_WORKER_RUNS_GENERATION` | Generation in the worker | see `docs/operations/api-worker-split.md` | as there |

Migrations 0034 to 0044 are additive; each has a tested downgrade
(`tests/test_quiz_runtime_tables.py`). If `main` gains migrations, renumber `down_revision` and
`schema_revision.py` at merge time.

## What still needs people

- A live-model run of every role and of `scripts/dev/benchmark.py` (needs a key).
- Qualified reviewers for a sample of generated courses (`benchmark.HUMAN_REVIEW`) and for the
  Learning Evidence Library.
- Named people to confirm lessons marked `human_review_required` and to grade performance tasks.
