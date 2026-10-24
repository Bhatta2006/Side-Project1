# Course generation: any course, built in batches by agents

- **Status:** Draft for owner review (2026-10-24)
- **Supersedes in part:** ADR-0002 ("AI cannot freely generate a curriculum") — see §12
- **Builds on:** ADR-0003 (skill-pack contract), ADR-0004 (append-only evidence), ADR-0005 (isolated execution)

## 1. Goal

Create a complete new course (ML Engineer, AI Basics, anything) from a short brief, with
the depth and quality of the hand-authored DSA course, without a human writing the
curriculum. The outline is generated once. Lesson content is generated in small batches,
just ahead of the first learner who needs it. Adaptivity, mastery, planning and tracking
work the same as today.

**Not in this version:** per-learner private content, learner-typed topics (phase G6), and
migrating DSA, CP or Zero into the pipeline.

## 2. Decisions (owner, 2026-10-24)

| Topic | Decision |
|---|---|
| Who starts a course | Admin writes a brief. Learner-requested topics come later on the same pipeline |
| Sharing | One canonical course. Each batch is generated once, when the first learner approaches it, and cached for everyone |
| Release | Deterministic checks, then an independent reviewer agent, then auto-release. Labelled AI-generated, learners can report problems, batches can be quarantined |
| Assessment | Code (existing judge), auto-graded quizzes, AI-rubric free text, projects |
| Runtime | In-product background worker, one agent per role |
| Storage | DB, versioned, with status and provenance. Repo YAML stays as the gold packs |
| Existing courses | DSA, CP and Zero stay hand-authored. They serve as few-shot examples and as the review bar |
| Depth | The enrollment goal (overview / practitioner / mastery) selects concepts. "Go deeper" sub-batches are shared once generated |
| Grounding | A researcher agent uses the web, cites sources and never copies |
| Models | Provider-agnostic, configured per agent role |
| Latency | Prefetch about 2 concepts ahead. If content isn't ready, hold and offer review/practice |
| Budget | Configurable caps per course and per batch. Generation pauses and alerts when one is reached |
| Syllabus | Full outline up front. Content is generated lazily |
| Languages | Declared per course in the brief |

## 3. Shape of a generated course

```
Brief ──► Outline (whole course, once) ──► Concept packages (lazy, a few at a time)
          modules, concepts, prereq DAG,     lesson, atoms, quiz items, exercises,
          objectives, misconceptions,        project (per module), sources
          depth tags, assessment plan
```

- **Brief** (admin input, ~1 page): title, audience, outcome ("can train and ship a
  classifier"), languages, assumed background, known-good references, budget, and which
  existing concepts to reuse as prerequisites (e.g. `zero:loops`, `dsa:complexity`).
- **Outline**: the same `Course` / `Module` / `Concept` schema as today, but each concept
  has `status: planned`, meaning it has a title, summary, objectives, prerequisites,
  misconceptions, a depth tag and an assessment plan, but no lesson yet. Placement, the
  roadmap and the planner can see the whole course from day one.
- **Concept package**: one concept's learner-facing content, built against today's
  schemas (`Concept.lesson`, `AtomPack`, `QuizItem`, `Problem`, quiz families). This
  package is the unit of generation, review, release and quarantine.
- **Batch**: the concept packages queued together by a single trigger (usually the next
  1–3 concepts on a learner's frontier).

Every agent produces output in a **schema that already exists**, so the existing
validators (`catalog/validate.py`, `validate_atoms.py`, `validate_problems.py`,
`validate_quiz.py`) are the first quality gate without changes. New schema is needed only
for `planned` status, free-text rubric items and projects.

## 4. Agents

Each agent works on one artifact for one concept. It gets only the context it needs and
returns JSON matching a schema. Agents never write to the DB. The orchestrator is
deterministic code: it validates, stores and moves state forward (ADR-0002 still holds
for writes).

| Role | Input | Output | Runs |
|---|---|---|---|
| **Course Architect** | Brief, list of existing concept IDs, gold outline excerpts | Outline: modules, concepts, DAG, objectives, misconceptions, depth tags, assessment plan, estimated minutes | Once per course, plus each "go deeper" |
| **Curriculum Critic** | Outline, brief | Pass or revise with notes: gaps, concepts that are too broad (per content-standard), ordering, cycles, coverage of the outcome | After Architect, max 2 rounds |
| **Researcher** | One concept's outline entry | Source pack: 3–8 sources (url, title, license, retrieved_at, sha) with extracted factual notes and claims. No learner-facing prose | Per concept package |
| **Lesson Author** | Outline entry, prerequisite summaries, source notes, 1–2 gold DSA lessons as examples | `lesson` markdown, `key_points`, `pitfalls`, `resources`. Must include worked traces, correctness reasoning, edge cases and self-checks, as DSA lessons do | Per concept |
| **Atom Author** | Lesson, misconceptions | `AtomPack` (hook, concept, worked, predict, trace, micro…) within the existing word/line limits | Per concept |
| **Assessment Builder** | Lesson, objectives, assessment plan | Quiz items (mcq/output/bug/numeric), free-text prompts with rubrics | Per concept |
| **Exercise Engineer** | Lesson, course languages | `Problem` with `reference`, `brute`, `generator`, `small_generator`, `starter` per language | Per concept where the plan says code |
| **Project Designer** | The module's concepts | Capstone brief, milestones, rubric, automated checks | Per module, when its last concept is queued |
| **Fact Checker** | Package plus source pack | A list of claims, each marked supported, unsupported or contradicted, with its source | Per package |
| **Reviewer** | Package, outline entry, gold examples, rubric | Scores per dimension (§6). Pass, or revise with specific notes per artifact | Per package, max 2 revise rounds |

Model, provider and effort are set **per role** in config (e.g. `SOCRAT_GEN_MODEL_ARCHITECT`,
`SOCRAT_GEN_PROVIDER_REVIEWER`), using the existing `assistant/gateway.make_provider`. The
Reviewer and Fact Checker should use a different model, or at least a different prompt
lineage, from the authors so they don't share blind spots.

## 5. Batch lifecycle

```
planned ─► queued ─► researching ─► authoring ─► checking ─► reviewing ─► released
                                        ▲             │            │
                                        └── revise ◄──┴────────────┘ (≤2 rounds)
                         any state ─► failed (needs admin)   released ─► quarantined ─► queued
```

- **Jobs** are rows in a `gen_job` table, picked up by the worker (same pattern as the
  outbox consumer in `worker.py`). A job is unique per `(course, concept, outline_version,
  stage)`, so duplicate triggers are no-ops.
- **Order inside a package:** Researcher → Lesson → (Atoms ‖ Assessment ‖ Exercise) →
  Fact Checker → deterministic checks → Reviewer. A failing artifact goes back to its own
  author with the notes, not the whole package.
- **Triggers** (outbox events already exist): `enrollment.created`, `activity.completed`,
  and `learning.band_changed`. On each one, the orchestrator asks the planner (`plan_for`)
  for the learner's next K concepts (default K=2, configurable). It queues any that are
  `planned`, highest priority first, ordered by how soon a learner needs them.
- **Hold state:** if a learner reaches a concept that isn't released, the planner skips
  it as unavailable (a missing language variant is already handled the same way). It
  offers review, practice or a parallel unlocked concept, and shows "being prepared". It
  never serves a draft.

## 6. Quality gates

Gates run in order. The first failure sends the artifact back to its author.

1. **Schema**: the existing Pydantic models and validators. Concept IDs must exist and
   the DAG must be acyclic (`graphlib`, already in `registry.py`).
2. **Executable**: references, brutes and generators run **only in the execution service**
   (ADR-0005), never in the API process. The reference must agree with the brute on small
   cases, a deliberately wrong solution must fail, and every language variant must
   produce the same results. Quiz `output` items: the code is run and the result must
   match the stated answer. Tests are generated at release and stored with the package
   (this replaces the build-time `.cache/content-tests` step for generated courses).
3. **Originality**: deterministic n-gram overlap against the fetched source text. Above
   the threshold, the artifact is rejected and the source is never copied.
4. **Fact check**: zero "contradicted" claims. "Unsupported" claims must be rewritten or
   cited.
5. **Reviewer rubric**, each scored 1–5. To pass, every dimension needs ≥4 and correctness
   needs 5:
   correctness · depth against the gold DSA lesson (worked trace, why it works, edge cases,
   self-checks) · continuity with prerequisites · misconception coverage ·
   assessment/objective alignment · clarity and length · accessibility.
6. **Release**: the package becomes `released`, gets an immutable version and has
   provenance (`origin: original`, sources as `SourceRef`, `review.by: <reviewer model>`).
   An event is emitted, and the catalog picks it up (§8).

After release:
- learner reports go through `content.issue_reported`;
- when the report rate rises or quiz items look anomalous (calibration already tracks
  this), the package is automatically quarantined;
- a quarantined package falls back to hold and a regeneration job is queued with the
  report text attached.

**Quality eval (pre-launch and in CI):** run the pipeline on 5 concepts that already
have gold DSA versions, and blind-compare them with the Reviewer and the owner. Track
pass rate, revision rounds, cost per concept and judge-test pass rate. `assistant/evals.py`
is the starting point.

## 7. Depth

- Each outline concept has `depth: overview | practitioner | mastery`, the lowest goal
  that needs it.
- The enrollment goal filters the curriculum (`service.curriculum`). Concepts above the
  learner's goal show as optional: visible, and they can be taken.
- **Go deeper** on any released concept runs the Architect on just that concept. It
  proposes 2–6 child concepts (`parent: <concept>`, `depth: mastery`), the Critic checks
  them, and they enter the outline as `planned`. They are shared: the first request pays
  for them and later learners see them immediately.

## 8. Data model and catalog integration

New tables (SQLAlchemy + Alembic, as in `services/api/migrations`). G0 ships the first two as
`generated_courses` and `generated_concepts`. The rest arrive with the phase that first uses them:

- `gen_course`: id, brief (json), languages, status, outline_version, budget_usd, spent_usd, created_by
- `gen_concept`: course_id, concept_id, outline fields (json), depth, parent, status, released_version
- `gen_artifact`: course_id, concept_id, kind (lesson / atoms / quiz / problem / project / rubric), version, payload (json, existing schema), status, provenance, created_at — append-only versions
- `gen_source`: id, url, title, license, retrieved_at, sha256, notes (json)
- `gen_job`: id, kind, target, stage, state, attempts, model, provider, input_tokens, output_tokens, cost_usd, error, timestamps
- `gen_review`: artifact_id, reviewer model, scores (json), notes, verdict

Catalog: `default_catalog()` stays the file loader for gold packs. `generated.merged()`
(called from `learn.routes.catalog()`) merges file courses with DB courses (released packages become
`live` concepts; outline-only concepts become `planned`). It is cached per process,
keyed on the latest release sequence number. The release event bumps the key. Planner,
mastery, placement, quiz and library keep receiving a `Catalog` and **do not change**.
Concept IDs use the existing `course:concept` scheme, so generated courses can depend on
`zero:*` and `dsa:*`.

## 9. Assessment and mastery

| Mode | Grading | Evidence kind |
|---|---|---|
| Code exercise | Existing judge + execution service | existing (`independent_solve`, …) |
| Quiz (mcq/output/bug/numeric) | Deterministic | existing quiz evidence |
| Free-text explain | LLM grades against a released rubric. The score is capped and the grade is logged | new `explain`, weighted lower |
| Project | Automated checks + rubric grading per milestone | new `project` |

Mastery stays deterministic (`mastery/model.py`). Free-text evidence alone can never
mark a concept mastered: `step_cap` gets a lower cap for `explain`, and mastery requires
at least one deterministic piece of evidence. This keeps ADR-0004 replay meaningful.

## 10. Budgets and providers

- An estimate is made at outline time: `concepts × per-concept cost by role`, using the
  configured price per role. If it exceeds the course budget, the brief is refused before
  any spend.
- Every agent call records tokens and cost on `gen_job`, reusing `assistant/budget.cost`
  with per-role prices.
- When `spent_usd ≥ budget_usd`, or a batch passes its cap, the course pauses. No new
  jobs start, an admin alert event is emitted, and learners see hold state.
- Revise rounds are capped at 2. A package that still fails goes to `failed` in the admin
  queue and is not retried endlessly.

## 11. Safety

- Fetched web pages are untrusted. The Researcher returns notes only. Authors never see
  raw page text, so injected instructions in a page can't reach authoring prompts. Notes
  are length-limited and stripped of markup.
- All generated code runs in the execution sandbox with the existing limits.
- Generated packages carry an "AI-generated" label in the UI and a report button.
- Learner-requested courses (G6) also need topic moderation, a per-learner course quota,
  and admin approval or auto-approval of the outline.

## 12. ADR changes

ADR-0008 (to be written on approval): **AI may generate course content as data, under
deterministic gates.** It amends ADR-0002 as follows:
- AI may generate outlines and content;
- deterministic services still own eligibility, prerequisites, mastery, planning,
  assessment scoring and all writes;
- no model identity gets DB credentials;
- released content is immutable and versioned (ADR-0003);
- content-standard principle 4 becomes "AI may draft; only gates release".

## 13. Rollout (thin slices, each usable on its own)

| Phase | Delivers | Done when |
|---|---|---|
| G0 ✅ | `generated_courses` / `generated_concepts` tables, `planned` status, merged catalog (`catalog/generated.py`), ADR-0008 | A learner can enroll in a DB course and see planned concepts on the roadmap. All existing tests pass |
| G1 ✅ | Brief → Architect → Critic → outline (`socrat/coursegen`), `generation_jobs` + in-process runner, per-role models (`SOCRAT_GEN_ROLES`), admin Courses tab to brief, follow, edit (JSON), revise and publish | The "AI Basics" outline is produced and reviewed in the admin UI (verified with a scripted provider; a live-model run is still to do) |
| G2 ✅ | Package pipeline (`coursegen/package.py`): Lesson Author → Quiz Builder ‖ Atom Author → gates (schema, depth by tag, headings, self-checks, course languages, public-https link check) → Fact Checker ‖ Reviewer → release; per-artifact revisions, 3 rounds; released atom packs served; lessons labelled AI-generated. Admin writes concepts one by one or the next 3. **Deferred:** web Researcher and the originality gate (need a search provider choice), code/output quiz items and atom code adapters (done in G4) | Concepts of a published course release end-to-end (verified with scripted models; a live-model gold comparison is still to do) |
| G3 ✅ | Prefetch (`coursegen/prefetch.py`): enrolling, placement and each completed activity queue the learner's current concept and the two after it (once; a failed concept waits for the owner); planned concepts are held with a "being written" nudge. Budgets: reaching the course budget pauses the course and requeues the job; a per-concept cap ends that job. Owner pause, resume and budget editing in the admin sheet. Quarantine (`coursegen/quality.py`): 3 distinct learners reporting a released concept (`SOCRAT_GEN_QUARANTINE_REPORTS`), or the owner withdrawing it, sends it back to planned and queues a rewrite with the reports and the previous version | Prefetch, hold, budget pause and quarantine-and-rewrite verified with scripted models; the 10-concept live walk-through waits for a live-model run |
| G4 ✅ | Exercise Engineer (`coursegen/exercise.py`): one judged problem per `exercise` job, queued when a released concept's outline asks for code (or by the owner). Its generators, Python reference, brute force, other-language references and a deliberately wrong solution run in the execution plane (`coursegen/execute.py`: signed `verify` jobs with no learner, claimed by the existing workers); release needs the examples to match, brute and reference to agree on small inputs, every language to agree, the wrong solution to fail and ≥3 hidden tests, then a reviewer. Tests are stored with the problem (`generated_concepts.problems`). Packages may carry `output` quiz items and atom code adapters when every course language has a worker; both are run, and the checkers see the real output. **Limit:** production runs learner code in the browser and has no server workers, so code generation waits (`execution_unavailable`) until the gVisor runner host is deployed | A learner is judged on a generated exercise (wrong answer rejected, reference accepted), verified with scripted models and a test worker; a live-model run is still to do |
| G5 | Free-text rubric grading, projects, new evidence kinds | Mastery is reached in a non-code course |
| G6 | "Go deeper", learner-requested courses with moderation | A learner-requested topic produces a reviewed outline |

## 14. Risks and open points

- **Depth drift**: authors write shallower than DSA. Mitigations: gold examples in every
  author prompt, depth as a hard reviewer dimension, and the G2 eval as the go/no-go.
- **First-learner latency**: a package takes an estimated 5–15 minutes. K=2 prefetch should
  cover typical pace. Measure it in G3 and raise K for fast learners.
- **Outline mistakes are expensive later.** The outline is versioned, and changing it
  after packages exist needs a migration (renamed or split concepts carry evidence over
  by id map), like `former_ids` on quiz items today.
- **Reviewer collusion** (the same model family approving its own style). Use a different
  provider or model for the Reviewer where possible, and have a human spot-check a sample
  of releases.
- **Licensing**: sources must have a known license before their notes are used. This
  reuses the `content/sources/registry.yaml` license gate idea, applied per `gen_source`.
