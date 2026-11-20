# Course generator: backlog

Everything left to finish the course generator, written 2026-11-20 on `gbuild/feat/course-generator` at
`2ea23c10` so the build can continue without the person who wrote it. Each item names where the code goes,
what "done" means, and what it depends on. Items are in the order I would do them.

Before you start, read: `AGENTS.md` (rules), `HANDOFF.md` section 2 (Windows, CRLF, `--basetemp`),
`lesson0-generation-plan.md` (implementation status at the top), `course-brain-plan.md` (implementation
status), `generation-plug-points.md`, `learner-memory.md` (anything that reads the learner goes through
`socrat.learner`; update that doc in the same change), `onboarding-handoff.md` (the contract with `/start`).

Rules that apply to every item: new behaviour defaults off behind a flag; migrations are additive with a
tested downgrade (the next free number is `0053`, `down_revision = "0052_learner_profile"`); models
explain, code verifies; say what is not verified; stage specific paths only; never commit
`apps/web/next-env.d.ts`, `.env`, `uv.lock`, `skills-lock.json`, `.claude/launch.json`, `.gitignore`,
`services/api/src/socrat/lifecycle.py` or `services/api/tests/test_lifecycle.py` (untracked, someone else's).
Run tests from the repo root:
`uv run --project services/api pytest services/api/tests/<file> -q --basetemp .cache/pt/<dir> -p no:cacheprovider`.

---

## 0. Where it stands

**Built and tested with scripted model replies** (nothing below has run against a live model):

| Area | What | Flag | Tests |
|---|---|---|---|
| Course brain | on-demand subject roots, `CourseSpec`, reuse of a compatible course, in-flight joining, privacy for shared courses (`shared_intent`, leakage gate), root units + research job, corrections, admin JSON routes | `course_brain` | `test_course_brain.py`, `test_brain_units.py` |
| Learner hooks | outline, lessons and quizzes of a private course read the learner's brief through `brain/learner.py`; quiz options tagged with misconception ids | `gen_learner_brief` | `test_learner_hooks.py`, `test_learner_generation.py` |
| Lesson 0 plan, PR 0-1 | profile loader, `Brief.plan`, explicit asks enforced on the style, gap -> probe quiz item | `gen_learner_plan` | `test_learner_plan.py` |
| PR 2 (part) | roadmap sized by mode, module 1 detailed, later modules detailed on demand, critic no longer blocks | `gen_learner_plan` | `test_roadmap.py` |
| PR 3 (API) | `view.start` readiness field | always on (additive field) | `test_start_state.py` |
| PR 4 (part) | true session minutes travel to enrolment; days packed to them | always on for Lesson 0 courses (additive) | `test_true_session_budget.py` |
| PR 5 | heartbeat, 2-minute re-claim, learner-only worker slot, resume from stored outline | `gen_waiting_learner` | `test_waiting_learner.py` |
| PR 6 (part) | probe miss marked on evidence; example / review / stretch after session one | `session_one_adaptation` | `test_session_one.py` |

What the generator produces today: course plan (outline), lessons, concept quizzes (keyed by code, with
misconception tags and the Lesson 0 probe item), the starting-level diagnostic, Apply lessons with a
rubric-graded answer, coding exercises (code-shaped courses only) and projects. Module checkpoints,
reviews and test-outs are assembled from the concept quiz items; there is no separate exam writer.

**Test status:** last complete full run, before PR 5 and PR 6 (at `2317ed9c`): 1094 passed, 25 skipped, 5 failed.
All 5 failures predate this work: `test_lifecycle.py` x3 (untracked file),
`test_explainer.py::test_artifact_validation_and_compiler_boundaries` (theme token),
`test_sourced_content.py::test_a_researched_lesson_is_sent_back_until_it_cites_and_then_credits_its_sources`.
PR 5 and PR 6 were checked with the related suites only (generation/jobs 95 passed, planner/quiz/learner 84 + 43
passed). Re-run the full suite before anything else (item 1.1).

---

## 1. Do first

### 1.1 Full suite on the current head (done 2026-11-20)
**Result at `9ee458f`:** 1081 passed, 25 skipped, 25 failed. None from generation. The 25: the two known
(`test_explainer` theme token, `test_sourced_content`); `test_admin_drafts.py` x3, which copy `content/courses`,
gone since the built-in courses were removed (stale tests, not fixed here); and 20 cpp/java runs in
`test_local_backend.py` / `test_native_limits.py` because this machine has no `g++` or `java` on PATH.
`test_lifecycle.py` is absent from this checkout. Original instruction:
Run the whole API suite once (about 12 minutes) and confirm only the 5 known failures remain. If anything
else is red, it is most likely `learn.service.history_for` (it now also returns `at` and `details`) or
`planner.engine.build_plan` (new `strict` argument, session-one branch).

### 1.2 First live model run (done 2026-11-20, see `live-run-log.md` "Live run 2")
Run A (brain off): roadmap 75 s, first lesson 196 s, outline $0.18, first lesson $0.34, 5 modules / 15 concepts,
door in lesson 1, probe item present. Run B (brain on): Lesson 0 plan not used (B1), SQL fences rejected (B2),
reused outline never started its first lesson (B3, fixed), a 567 s model call (B4). Still open: the second learner
served from a *published* shared course with zero model calls (B5), and a live run of 2.2 / 2.3.
Original instruction:
Nothing has run against a real model. With a key (Vertex or Anthropic; ask the owner, never guess), turn on
`learning_requests_enabled`, `gen_learner_plan`, `gen_learner_brief`, `gen_waiting_learner`,
`session_one_adaptation` locally, go through `/start` once with the SQL goal from `onboarding-handoff.md` 4,
and record in `live-run-log.md`: time to roadmap, time to first lesson, outline cost, number of modules and
concepts against the mode caps, whether the door and the probe item appear in lesson 1, and the job log
events (`profile_*`, `kept_for_learner`, `constraint_unmet`, `outline_stored`). Then repeat with `course_brain`
on and a second account asking for the same thing (it should be served, zero model calls).
**Done when** the run is logged with numbers and every surprise has an item in this file.

### 1.3 Put strict lesson gates back before real learners
Code status 2026-11-20: `gen_relaxed_gates` defaults to off, config refuses it in staging and production, and it
is not set in the repo's `.env` / `.env.local`. What remains is a check of the deployed environment's variables
(not visible from the repo). Since 2026-11-11 the strict lesson gates are relaxed in the live AI API for testing. Turn them back on before
any real learner uses generated courses (owner's standing instruction).

---

## 2. Lesson 0 -> generation (`lesson0-generation-plan.md`)

### 2.1 PR 2 rest: `outcome_spec` and `gap_map` from the architect (done 2026-11-20)
Built as specified; a rejected outcome is dropped and logged (`outcome_rejected`) rather than costing another
architect round. Details in `lesson0-generation-plan.md` (PR 2 rest). Tests in `test_roadmap.py`.
- **What:** the architect reply gains `outcome_spec` `{final_task, success[], constraints_kept[], assumptions[]}`
  (plan section 4.A) and `gap_map` `[{gap, concept|null, confidence: match|possible|none}]` (section 2.3).
- **Where:** `coursegen/outline.py` (`ARCHITECT` text, the `SHAPE` reply format, `to_course`/`tidy`), `learner_plan.py`
  (use `gap_map` when present, keep the deterministic matcher `gap_concepts` as the fallback and as a check),
  `jobs.run_outline` (store both in the brief or course), `package.py` (lesson author reads `final_task`).
- **Code checks:** every `LearnerPlan.constraints[].quote` appears in `constraints_kept`; each success criterion
  starts with a verb (same check as objectives); a requirement the learner did not give must be under
  `assumptions`; a `possible`/`none` gap never produces a probe.
- **Done when:** tests reject an outcome missing a constraint quote; an ambiguous gap gives no probe; admin
  briefs unchanged.

### 2.2 PR 2 rest: first lesson in parallel with the critic (done 2026-11-20, `gen_waiting_learner`)
Live run A measured the gain this removes: 32 s between module-1 details and the critic's answer. Tests in
`test_roadmap.py`; `test_waiting_learner.py` now expects the course saved before a crash at the final save.
Not measured live yet.
Today the first lesson is queued at save (`early_first_lesson`). With `gen_waiting_learner` the learner slot
exists, so queue the first concept's package job as soon as module 1 is valid, before the critic answers; if the
critic's one repair round changes module 1, cancel and re-queue that job. **Where:** `jobs.run_outline`.
**Done when:** with a scripted slow critic, the first lesson's package job starts before the critic reply; a
repair of module 1 re-queues it once.

### 2.3 PR 4 rest: computed activity minutes and the session-total gate (done 2026-11-20)
Owner decision: changing minutes per day in settings updates `goal.session_minutes`. The gate lives in the package
job (`jobs.first_session_over`), which sees the quiz; `check_lesson` sees only the lesson. Word count is read from
the written lesson at plan time, not stored. Tests in `test_true_session_budget.py`.
- **What:** for a written concept, minutes are computed, not estimated: reading `ceil(words / 180)`, `0.75` min per
  quiz item, a fixed attempt allowance per exercise, `2` min feedback per check (plan 3.4). Unwritten concepts keep
  the ratio. `package.check_lesson` fails a first lesson whose total exceeds `session_minutes * 1.1`.
- **Where:** `planner/engine.concept_activities` (needs the written lesson's word count; store it on the concept at
  `store_concept`), `coursegen/package.py`.
- **Also:** `ScheduleUpdate` (`learn/routes.py`) does not touch `goal.session_minutes`; decide with the owner
  whether changing minutes per day in settings should clear or update it.
- **Done when:** a 10-minute learner's day 1 sums to <= 10 computed minutes; a too-long first lesson goes back.

### 2.4 PR 6 rest: smaller quiz band, Ladder ceiling, bridge proposal (done 2026-11-20)
Built behind `session_one_adaptation`; tutor turns count as help (owner decision). Details in
`lesson0-generation-plan.md` (PR 6 rest). The new-context review item waits on 4.2. Original item:
- After "difficulty" in session one: a smaller quiz band for that concept and the tutor's Ladder ceiling lowered
  one level (`assistant/socratic.py` start ceiling); at most one bridge concept through the existing proposal flow
  (`evolve.insert_bridge`, learner accepts).
- "Help" is only seen where it is recorded (code submissions and labs). Lessons and quizzes record no hint use,
  so a quiz-only course always reads as "independent". Decide whether tutor turns on a concept count as help
  (that is a learner-layer read: go through `socrat.learner`).
- The `review` retrieval reuses the concept's own quiz items; a "new context" item needs generated variants.
- **Done when:** the three branches of plan 4.E produce the specified next-session items from scripted evidence.

### 2.5 PR 7: benchmark and first-lesson quality gate (done 2026-11-20, partly measured)
Built: the script, `ms` on the skeleton and critic log entries, and the gate (`jobs.first_lesson_issues`: session fit, door in the first 150 words, an asked-for code language, a keyed check; sent back while rounds remain, waived and logged on the last). Measured: 6 SQL runs (`live-run-log.md` live run 3); the exam and non-programming goals were not run (owner stopped at $4.72). To finish the table, rerun the script with `SOCRAT_ONBOARDING_PER_HOUR=1000` on the API. Not checked by code: one example outside the door. Original item:
- `scripts/dev/bench_claim_to_today.py`: three goals (SQL, an exam, a non-programming one) x three modes x 10/25
  minutes, run against the real worker; report T1 (roadmap), T2 (first lesson live), outline end, cost by job kind
  from `GenerationJob.log[].at` and `cost_usd`; cross-check with `/api/v1/admin/engine-costs`. Add `ms` to the
  outline job's `_note` entries (`reply.ms` exists).
- `tests/test_first_lesson_gate.py`: the first lesson passes `pkg.check_lesson`, shows each constraint's effect,
  has the door in its intro plus one example outside it, carries the probe when a gap matched, has an action with a
  key or a labelled rubric, and fits the session (2.3). The gate is code.
- Targets to measure against (proposals, not facts): roadmap <= 60 s, first lesson <= 150 s, outline <= $0.25, first
  lesson <= $0.15. Append results to `live-run-log.md`.

### 2.6 The acceptance test, claim -> Today (done 2026-11-20)
`services/api/tests/test_claim_to_today.py`: two learners through the real routes (onboarding, claim, the
outline and package jobs, publish, enrol, `/today`) with one scripted model that writes only from what its
prompts carry. Learner A (door "Split trip expenses", snag missed once) gets the door and the gap in the
author's `<learner>` block, a lesson that opens with the door, a probe item, `session_minutes` at enrolment and
Today's `next` on that lesson; learner B (another door, no miss) gets the other door and no probe, and the rest
of the lesson is identical. Not covered: the concept route's view of the probe (checked on the catalog).
Original item:
One test (plan section 8): a single learner answer (a door or a gap) traced through claim -> outline (scripted) ->
first lesson prompt (as quoted data) -> released lesson (door intro, probe item) -> publish -> enrol with
`session_minutes` -> `/today` `next` is the first lesson -> the concept returns the probe. Changing the answer
changes exactly those items. Not written yet; the pieces are tested separately.

### 2.7 Starting level from calibration (done 2026-11-20, as an offer)
Placement marks every concept a later level skips as placed-known without a question, so applying a level
from Lesson 0 would break "never mark a concept known from Lesson 0 alone". Built instead:
`learner_plan.suggest_level` (code) and `view.level_suggestion` `{level, start, reason}`; `enroll.level` is
unchanged and the learner chooses. Rule: snag solved first try with no hint, no gap, pace not slow; the latest
level whose start is at most one concept after the probed one (`learner_plan.teaching`, the gap matcher). Contract
in `onboarding-handoff.md` 3.3; the `/start` page does not show it yet (onboarding's call). Original item:
Lesson 0 runs no diagnostic, so `view.enroll.level` is the course's first level (`onboarding-handoff.md` 4.4). Use
the profile's `calibration` to choose the start level (code, not a model), and never mark a concept known from
Lesson 0 alone. **Where:** `coursegen/requests.view` (`enroll.level`), `learner_plan.py`. Coordinate with onboarding.

### 2.8 PR 8 (optional): SQL checker
Stopgap since 2026-11-20 (owner decision): a code course accepts ```` ```sql ```` blocks for display (`package._common_lesson_checks`); nothing runs them.
A `harness/` capability on stdlib `sqlite3` so a "write the query" exercise is graded by running the learner's
query and the reference on a fixture table. Until then SQL practice is predict-the-result items with a key.
**Where:** `harness/`, `coursegen/exercise.py`, `catalog/schema.py` (`Language` or a `grader` field).

### 2.9 Plan pieces deliberately left out (decide if still wanted)
`Constraint` kinds `format`, `syllabus`, `other`; the stylist reading `request` instead of `style_request`;
`gen_lesson_pages` for Lesson 0 courses (off; needs its own quality check).

---

## 3. Course brain (`course-brain-plan.md`)

### 3.1 Shadow mode and rollout
Not built. With serving off, `route` should still run and write `course_matches` with `outcome` and `would_serve`,
changing nothing for the learner (plan 5.6, PR B). Needed before turning `course_brain` on for real learners.

### 3.2 Backfill script (PR G)
`scripts/dev/backfill_roots.py`: assign `root_id` to existing learner courses by `roots.resolve` on stored
`LearningRequest.intent` (alias tables only, no model), always `serve='private'`. **Done when:** legacy rows get a
root, nothing a learner sees changes (snapshot test of `view` for old requests).

### 3.3 Delivery-time adaptation from the overlay (PR H)
`POST /enrollments` copies the served learner's private overlay into `Enrollment.learner_plan`, but nothing reads
it. The planner and tutor should: session minutes from it (as PR 4 does for built courses), probe insertion for the
learner's own gaps on a shared course, Ladder start. **Where:** `planner/engine.py`, `learn/service.py`, tutor.
Read it through `socrat.learner` and record it in `learner-memory.md`.

### 3.4 Reuse quality: gold set, concurrency, crash tests
- A labelled gold set of at least 60 request pairs (`test_brain_compat.py`): false reuse must be 0, missed reuse
  reported; near misses (depth, rigor, language, register, tools, assessment, themed vs not) rejected.
- `concurrent_first_requests`: 8 threads claim compatible requests on a fresh DB; one root, one family course,
  one outline job, one research job per unit.
- `resume_after_research_crash` (units are not researched twice).
- `scripts/dev/bench_brain.py`: cold / from existing material / direct reuse, timed and costed separately.

### 3.5 Scoper
Not built: a fast-model step that splits a topic into several units `{unit_key, title, depth, prerequisites}`.
Today one unit per canonical topic and depth.

### 3.6 Scheduled refresh of stale units
A stale unit is refreshed only when a later request needs it. Add a periodic sweep (worker) that queues research
for units past their refresh age.

### 3.7 Admin web page
The JSON routes exist (`/api/v1/admin/brain/roots`, `/units?root=`, `/matches/{request_id}`,
`POST /units/{id}/correct`); there is no page. Read `apps/web/AGENTS.md` and `node_modules/next/dist/docs/`
first (Next 16, breaking changes).

### 3.8 Ownerless shared courses
A shared course keeps its first learner as `owner_id` (deliberate deviation). `regenerate` stays owner-only and
works only in review. Decide with the owner whether shared courses should become ownerless.

---

## 4. Quizzes and assessments

### 4.1 Exam writer (module or final)
No generator writes module or final exams. Checkpoints draw from the concept quiz items (`learn/quizzes.gate_pool`),
so they cannot ask harder, mixed or transfer questions. Proposal: an `exam` package kind per module (and a final one
built from `outcome_spec.final_task`, item 2.1), keyed by code like concept quizzes (`keyed.py`), mixing concepts,
with difficulty bands; gate it behind a flag.

### 4.2 Item variants for reviews
Reviews and session-one retrieval reuse the same items. Generate a few parallel variants per concept (same skill,
new context) so a review is not a repeat.

### 4.3 Misconception tags on older lessons
Quizzes are tagged only for lessons written from root units; earlier lessons carry no tags and the tutor's tag
for them is dropped (`learner-memory.md` 7).

### 4.4 Strictness stays the learner's
The learner chooses how strict the tutor, quizzes and assessments are. New assessment work must read that
setting, never hard-code strictness.

---

## 5. Web and onboarding (coordinate with the cofounder)

- **`/start` reads `view.start`:** enable "Start learning" at `first_lesson_ready`, show the plan at
  `roadmap_ready`, offer retry (`POST /learning-requests/{id}/regenerate`) at `first_lesson_failed`. The page is
  onboarding's; the contract is in `onboarding-handoff.md` 3.3. No change is needed for `enroll.session_minutes`.
- **Onboarding reshape:** the cofounder is reshaping onboarding to collect richer learner details. Any profile
  shape change bumps `PROFILE_SCHEMA`; update `learner_plan.load` and its tests in the same change.
- **E2E and visual specs:** the Playwright specs still onboard into removed courses. Re-seed them with a generated
  course (scripted provider) and get them green.
- **Learner profile screen** (partner's area): the API exists, no page.

---

## 6. Learner layer gaps that touch generation (`learner-memory.md` 7)

- A course shared later keeps lessons fitted to its owner; lessons written while private are not rewritten.
- The strategist gets a fixed `"unknown"` stage in `run_package`; passing `snap.concepts[c].stage` needs a second
  hook function in `brain/learner.py`.
- Mastery does not carry between courses; `user_brief.shown_elsewhere` only names titles.
- Lesson 0 `detected_gaps` are model labels; mapping is the deterministic matcher (item 2.1 adds `gap_map`).

---

## 7. Known risks in what is built

- **Live run 2 (2026-11-20):** a single model call can take ~570 s (B4). With `gen_waiting_learner` the heartbeat
  keeps that job alive, so the learner waits the whole call. Consider a shorter `ROLE_TIMEOUT` for jobs a learner
  waits on (priority <= 1), with the normal retry.
- **`course_brain` drops Lesson 0 entirely** for a new shared course (B1) until 3.3 is built: keep it off.
- **SQL courses are `python` code courses** (A1, B2): lessons wrap SQL in python fences or are sent back for
  ```` ```sql ````. Item 2.8 fixes the root cause; until then, allowing `sql` as a display-only fence is a one-line
  stopgap in `package._common_lesson_checks` (not done: owner's call).
- **2.2:** when the repair round changes module 1, a first lesson already *released* is reset to planned by the
  full save and written again (cost twice); a running one is cancelled and does not release.

- **PR 5:** a crash while module details are being written re-runs the architect (the outline is stored only
  once valid). A worker whose event loop is blocked for 2 minutes can lose its job to another worker; the job then
  runs twice (save is idempotent, cost is not). The 2-minute re-claim was not measured against a real worker kill.
- **PR 6:** `session_one` reads `history_for`'s 40-row window; once a learner has 40 evidence rows it returns
  nothing (by design: session one is long past).
- **PR 4:** a schedule change does not update `goal.session_minutes` (item 2.3).
- **Brain:** the leakage gate is 8-word shingles plus email and multi-word display name; short personal facts
  (a 3-word project name) are not caught. `shared_intent` relies on the onboarding sentence wording.

---

## 8. Turning it on

All new behaviour is off by default. Order to switch on once items 1.1-1.3 pass and the owner agrees:

1. `gen_learner_plan`, `gen_learner_brief` (private Lesson 0 courses fitted to the learner)
2. `gen_waiting_learner` (faster recovery, learner slot)
3. `session_one_adaptation` (stamped on new enrolments only)
4. `course_brain` after shadow mode (3.1) and the gold set (3.4) show zero false reuse

Keep the progress log in `lesson0-generation-plan.md` and `course-brain-plan.md` current, and tick items off here
as they land.
