# Universal Learning Engine: gap audit against the master prompt

Written 2026-11-03 against `feat/universal-engine` at `45cd247`, by reading the master prompt
(`SOCRAT_Universal_Learning_Engine_Master_Prompt.txt`, 1,141 lines, outside the repo) end to end
and the code it describes. The earlier plan (`universal-engine-plan.md`) mapped the prompt to
phases but mixed in an internationalisation track the prompt does not ask for, and never checked
the prompt's 20 acceptance criteria. This file does that, and judges **depth**, not only presence.

Verdicts: **Strong** (built, tested, would survive real use), **Partial** (built, but a required
part is missing or shallow), **Thin** (a stub or a model-trusting shortcut where the prompt asks for
verification), **Missing**.

## 0. Status after the gap work (2026-11-03, commits `0b3a697` to the item 12 commit)

| # | Criterion | Now | What changed |
|---|---|---|---|
| 1 | Natural-language request | Strong | unchanged |
| 2 | Inspectable blueprint | Strong | competency fields, graph checks, assumptions and unresolved questions |
| 3 | Prerequisites, objectives, path visible | Strong | every objective, effort, evidence, assumptions on `/new` |
| 4 | First modules without waiting | Done | first slice queued at publish from the diagnosed start |
| 5 | Durable background jobs | Strong | retries with backoff, dead-letter, lifecycle stages |
| 6 | Mixed activity types | Partial | tasks (reflection to practical) and an activity order; the page does not reorder by it yet; no audio or video upload |
| 7 | Sketch and 3D through the registry | Done | declarative sketches (flagged), `playground-visual` renderer |
| 8 | New renderer without the compiler | Strong | unchanged; README documents it |
| 9 | Resources traceable and cited | Partial | real search results only (flagged), provenance fields; no passage-level grounding; no live search run |
| 10 | Assessments with contracts | Strong | derived contract per assessment |
| 11 | Evidence recorded | Strong | plus person-graded performance evidence |
| 12 | Assisted vs independent | Strong | plus follow-up rule after a full solution |
| 13 | Next activity changes | Strong | plus bridge lessons for owned courses |
| 14 | Reviews | Strong | reasons, snooze, bring back; no cross-course review |
| 15 | Progress survives revisions | Partial | revisions keep evidence and objectives; a rewrite can still orphan quiz ids |
| 16 | Unsafe or invalid content flagged | Strong | five-state validation reports, deterministic safety notes |
| 17 | Recovery without duplicates | Strong | atomic claims, idempotent initial slice, dead-letter |
| 18 | Cost, latency, failures, outcomes measurable | Strong | latency per role, success and retry rates, outcome report |
| 19 | Existing functionality not broken | Partial | full API suite and new browser tests pass; older Playwright and visual suites still not run on the branch |
| 20 | Tests demonstrate behaviour | Partial | every item has tests; no live-model run; human review of the benchmark pending |

Still needs the owner: a model key for a live run, qualified reviewers (benchmark sample, evidence
library), named people to confirm lessons and grade tasks, and the decision to switch flags on.

## 1. Acceptance criteria (prompt section 20), as found before the work

| # | Criterion | Verdict | Evidence and what is wrong |
|---|---|---|---|
| 1 | Natural-language request | Strong | `coursegen/intent.py`, `requests.py`, `/new` |
| 2 | Structured, inspectable blueprint | Partial | Outline is a validated `Course`, but the competency fields the prompt lists (related, category, required evidence, practice types) do not exist; no prerequisite-analyst confidence or unresolved assumptions |
| 3 | Learner sees prerequisites, objectives, path | Partial | `/new` shows modules, first objective and "After:" prerequisites. Only one objective, no estimated effort, no graph view |
| 4 | First 3–4 modules usable without waiting | **Missing** | Nothing is generated at publish. `prefetch.py` writes 3 concepts ahead only after the learner enrols and opens Today; the first lesson is a planned stub at that moment |
| 5 | Later modules by durable background jobs | Partial | Jobs persist and are claimed atomically, stale jobs are reclaimed; triggering is per learner visit, not by progress threshold or estimated time |
| 6 | Mixed activity types | Partial | A concept can carry quiz, prompts, exercises, experiments, visuals, problems, projects. Fixed set of slots, no ordering, no reflection, case study, oral, performance, portfolio, audio or video activity |
| 7 | Existing sketch and 3D through the registry | **Missing** | The Playground 3D explainer (`explainer/`, declarative film JSON) is not a registered renderer. `concept-playground` is registered but not served, and its manifest describes model-designed code in an iframe, which the prompt forbids |
| 8 | New renderer without touching the compiler | Strong | `engine/renderers.register`, designer reads the registry |
| 9 | Resources relevant, traceable, cited | **Thin** | No search provider: the researcher recalls URLs from memory and code only checks they load. No chunk-to-claim grounding. `Resource` has no author, date, language, competency, sections, quality reasons, licence or citation |
| 10 | Assessments with objectives, scoring, validation | Partial | Quiz keys server-side, math via `math.check`, code judged, rubrics for prompts. No per-assessment record of competency, format, partial credit, alternate solutions, assistance allowed, evidence contributed |
| 11 | Activities record evidence | Strong (with gaps) | Quiz, code, exercises, experiments, prompts, projects write `Evidence`. Visuals write none (stated) |
| 12 | Assisted vs independent | Strong | `Evidence.assistance`, `mastery.ASSISTANCE` weights, help cannot manufacture mastery |
| 13 | Next activity changes with evidence | Strong | `planner/engine.py`, `adaptive/suggest.py`, `mentor/policy.py` (rules, reasons, undo, cooldowns) |
| 14 | Retrieval reviews scheduled and delivered | Partial | Expanding intervals, failures reset, `MAX_REVIEWS_PER_DAY`, reminders. No snooze or reschedule, no review reasons shown per item, no cross-course review |
| 15 | Progress survives refresh, sessions, revisions | Partial | Evidence is append-only; `concept_versions` keeps old text. A rewrite can orphan quiz ids (`maintain.lost_ids` reports, does not migrate) |
| 16 | Unsafe or invalid content blocked or flagged | Partial | Schema, fact-check `incorrect` blocks, reviewer, math checks, moderation. No persisted validation report with PASS / PASS_WITH_WARNINGS / NEEDS_REVISION / HUMAN_REVIEW_REQUIRED / REJECTED |
| 17 | Recovery without duplicates | Partial | Atomic claims, idempotent requests and stores. No retry count, no dead-letter state, a failed package stays failed forever (learner courses have no admin to retry it) |
| 18 | Cost, latency, failures, outcomes measurable | Partial | Cost per course and role, queue depth. No latency per role, success and retry rates, time-to-first-usable-module, or learning-outcome report |
| 19 | Existing functionality not broken | Partial | 798 API tests and new browser tests pass; older Playwright and visual suites never run on the branch |
| 20 | Tests demonstrate behaviours | Partial | Strong unit and e2e coverage for what exists; no generated-course benchmark |

## 2. Section by section

### 3. Course compiler
- Intent parser (3.1): **Strong.** Missing fields: intended use, deadline (the enrolment has a target date, the intent does not), language is the code language only.
- Diagnostic (3.2): **Partial.** Model-written, code-scored, no invented fallback. Does not use previous Socrat evidence; self-reported familiarity is the level pick only; result sets the level but does not seed per-competency state.
- Competency graph (3.3): **Partial.** `Concept` has id, objectives, prerequisites (multi, cross-course `Ref`), difficulty, misconceptions, assessment kinds. Missing: related competencies, knowledge or skill category, expected performance, required evidence, recommended practice types.
- Explicit stage contracts: **Partial.** Each role has a JSON shape and a validator, but there is no typed result envelope with evidence, assumptions, confidence and unresolved issues (prompt 7).

### 4. Learning experience schema
**Partial.** Course → modules → concepts, concepts carry typed activity slots. Course has a `version` string and concepts have version history (`concept_versions`); modules are not versioned on their own. No ordered activity list, so a module cannot say "explain, then simulate, then derive, then problem set" in an order.

### 5. Renderer registry
**Partial.** 8 typed manifests with every field the prompt asks for, deterministic selection, validated specs, accessible fallbacks, a web host that renders only approved components. Missing: the 3D Playground and sketch as renderers (criterion 7), automated renderer tests per manifest, a written plugin process.

### 6. Domain adapters
**Partial.** 6 adapters with verifiability, physical-practice and evaluator flags. Each adapter lacks terminology, competency structures and assessment types, and only math-science has its own validation tools (math, physics); electronics has no circuit or dimensional check beyond the physics `circuit` model; music has no rhythm or theory capability.

### 7. Orchestration
**Partial.** Roles: intent, architect, critic, researcher, author, quiz, atoms, facts, reviewer, experience, diagnostic, translator. Missing logical agents: Prerequisite Analyst and Pedagogical Strategist (no per-objective method choice with a reason). Budgets, timeouts, rounds exist. Missing: retry counts, prompt version on every artifact, per-module cancel and regenerate for learner courses, a typed result envelope.

### 8. Learning science
**Missing** as a library. Techniques exist in code (retrieval, spacing, worked examples, interleaving, transfer, stuck ladder) but there is no versioned Learning Evidence Library with definition, evidence quality, conditions, product rule, measure and references, and no strategy object a planner can choose and explain.

### 9. Adaptive engine (pre-dates this branch, the strongest part)
- Learner model (9.1): **Strong** core: Beta mastery with uncertainty, evidence count, assistance, misconceptions, review step. Missing: self-reported confidence, delayed-recall and transfer results as separate signals, scoring-policy version on the state.
- Evidence model (9.2): **Partial.** Kinds are activity-based (`quiz`, `code`, ...) not the prompt's cognitive types (exposure, recognition, recall, application, transfer, explanation, performance, delayed retention). A mapping is needed, not a rewrite.
- Mastery (9.3): **Strong**, interpretable and capped. Bands are `not_started / likely_known / developing / needs_practice / strong`; no "demonstrated" requiring independent performance; calibration exists for quiz items (`calibration/`) but not for the mastery thresholds.
- Next action (9.4): **Strong** for hand-authored courses; actions are not a single controlled enum with reasons.
- Hints (9.5): **Strong** (Socratic ladder 0–5, leak guard). Missing: after a full solution, an independent follow-up before mastery is explicit for code only.
- Reviews (9.6): **Partial** (see criterion 14).

### 10. Progressive generation
**Partial / Missing.** No initial slice at publish (criterion 4), no progress-threshold trigger, job states `queued|running|done|failed` instead of the prompt's state machine, no dead-letter, no "new module ready" notice, no bridge-unit insertion or accelerated path for generated courses, plan changes not versioned for the learner to inspect.

### 11. Research and resources
**Thin.** See criterion 9. Prompt-injection defence for retrieved text is moot today because nothing is retrieved; it must exist once retrieval does.

### 12. Quality gates
**Partial.** Deterministic: schema, math, physics, code tests, link checks, quiz answer-length rule, placeholder and number checks. Model: fact check, reviewer. Missing: a persisted validation report with the prompt's five states and structured findings, and "needs human review" as a state learners can see.

### 13. Data model
**Partial.** Most entities exist. Missing as first-class records: validation report and findings, prompt and policy versions, review events beyond evidence, assessment metadata.

### 14. Frontend
**Partial.** Honest states for planned concepts, approved renderers, fallbacks. Missing: citations shown with author and licence, "why this next" on generated courses (exists for hand-authored), live "new module ready" notice.

### 15. Safety
**Partial.** Adapter safety notes, moderation, minors' birth year, data export and erasure. Missing: high-stakes domain disclaimer (health, legal, finance) in the intent and lessons, refusal list for dangerous practicals in the author prompt checked by code.

### 16. Evaluation
**Missing** for generation (no benchmark of the 5 archetypes), **Partial** for outcomes (evidence supports it; no report of retention, transfer, hint dependence, calibration).

### 17. Unit economics
**Partial.** Per-role models, budgets, cost report. Missing: latency per role, cached reuse of identical non-personal structures.

### 19. Deliverables
Missing: README for adding a domain, activity type, renderer and learning strategy; current-state diagram; deployment notes for the engine flags together.

## 3. Things the prompt forbids that the code does

- `concept-playground` manifest describes "a model-designed interactive visual" in an iframe. The prompt says never run model-generated JavaScript in the browser. It is not served; it should be removed from the registry or redefined as a declarative spec.
- Learning-style language: `style/` and the "approach" pick are used as constraints on wording (allowed), but nothing stops a prompt from claiming a learner "is a visual learner". The author prompt should say preferences are usability constraints.

## 4. Order of work

Ordered by acceptance criteria failing first, then by dependency. Each is one or more commits with tests.

1. **Generation state machine and recovery** (crit. 4, 5, 17, 18): explicit states, retry count with backoff and dead-letter, prompt version and model on every artifact, initial slice generated at publish, progress-threshold prefetch, per-module cancel and regenerate, timings per role.
2. **Validation reports** (crit. 16): persisted report per artifact with the five states and structured findings; `HUMAN_REVIEW_REQUIRED` blocks release.
3. **Competency graph and assessment metadata** (crit. 2, 3, 10): additive schema fields, architect asked for them, critic checks them, `/new` shows them.
4. **Evidence taxonomy, demonstrated state, confidence** (crit. 12, 13): map kinds to cognitive types, "demonstrated" needs independent success after any full solution, optional confidence on quiz answers and calibration.
5. **Review queue controls** (crit. 14): snooze, reschedule, reasons.
6. **Resource intelligence** (crit. 9): provider-agnostic search interface with keyless connectors (Wikipedia, arXiv, Open Library), richer records, ranking with reasons, claim-to-source grounding, untrusted-text handling.
7. **3D and sketch through the registry** (crit. 7): register the Playground film player as a renderer; drop or redefine `concept-playground`.
8. **Activity sequence and new activity types** (crit. 6): ordered activities; reflection, case study, oral, performance, portfolio with rubrics flagged for a human evaluator.
9. **Learning Evidence Library and Pedagogical Strategist** (section 8): versioned library with real references, deterministic strategy choice per objective with a reason.
10. **Course evolution** (10.4): bridge units and accelerated path for generated courses, plan versions the learner can inspect.
11. **Evaluation harness** (crit. 18, 20): benchmark of the 5 archetypes with fixtures and metrics; learning-outcome report.
12. **Safety and the README** (15, 19).

What only the owner can give: a model key for a live run (every role has only seen hand-written replies), a search API key if a paid provider is wanted, qualified human reviewers for the benchmark and the Learning Evidence Library.
