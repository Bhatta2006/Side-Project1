# Course generation: plug points for other modules

The one page to read before plugging a module into course generation. Kept current by whoever
changes a plug point. Last updated 2026-11-20 (course brain, root units, learner-layer hook).

Related: `course-brain-plan.md` (why the brain exists), `lesson0-generation-plan.md` (onboarding
to generation), `onboarding-handoff.md` (the onboarding contract).

## 1. The learner layer (`socrat/learner/`, built in parallel)

Generation calls the learner layer **only** through `services/api/src/socrat/coursegen/brain/learner.py`.
When `socrat.learner` is importable and exposes `snapshot` and `brief`, it is used; otherwise every
hook returns nothing and generation runs exactly as before. Nothing else in `coursegen` imports it.

What generation expects from the layer (the read side in the layer's design):

```python
snapshot(db, enrollment, now) -> LearnerSnapshot
brief(snap, purpose, budget=...) -> dict      # purpose: "tutor" | "module" | "quiz"
```

`brief(..., "module")` must be a JSON-serialisable dict, prompt-safe (no raw learner text the
learner did not write for this purpose), and small: generation truncates it to 4,000 characters.
Suggested keys (generation passes them through unchanged, the lesson author reads them):
`skip` (concepts already shown), `patch_first` (weak prerequisites, misconceptions),
`review` (decaying concepts), `delivery` (length, tone, hint timing).

| Hook (in `brain/learner.py`) | Called from | When it applies | Status |
|---|---|---|---|
| `lesson_block(db, course_id, now)` | `jobs.run_package`, after the pedagogical-strategy block and root material | the course is **private** to one learner (owner set, `serve != "shared"`, not public) and that learner has an enrollment in it | built, tested with a fake layer (`tests/test_brain_units.py::test_learner_layer_shapes_private_lessons_only`) |
| `brief_for(db, enrollment, now, purpose)` | any generation code that needs the raw dict | as above | built |
| outline for a learner's new private course | `jobs.run_outline`, before the architect call | private course, learner already has other enrollments | **not built**: needs a user-level brief (`brief_for_user(db, user_id, now)`) because a new course has no enrollment yet. Add it to `brain/learner.py`, never call the layer from `run_outline` directly |
| quiz generation (`quiz` role in `run_package`) | `run_package` | private course | **not built**: use `brief_for(..., "quiz")` in the same place as `lesson_block` |

**Privacy rule (enforced in one place, `private_owner`).** A learner's brief may shape the lessons
of a course only that learner reads. Shared courses (served by the brain to other learners, or
shared publicly by their maker) are never written from one learner's brief. For those, the brief
shapes that learner's own sessions: planner order, quiz selection, tutor. That is the layer's
side, read from `Enrollment.learner_plan` and the layer's own data.

**Per-learner data generation already stores for the layer to read:**

| Where | What | Writer |
|---|---|---|
| `enrollments.learner_plan` (JSON) | the learner's request text, minutes, starting level, deadline, Lesson 0 mode, door, tone, calibration summary | `POST /enrollments`, copied from `course_matches.private` |
| `enrollments.match_id` | the routing decision that brought them to this course | same |
| `course_matches` (one per request) | spec, outcome, candidates and check results, adaptations, root units used | `coursegen.brain.route` |
| `onboarding.profile_for(db, request_id)` | the Lesson 0 profile | onboarding |

**Misconceptions for generated courses.** `catalog.misconceptions` is empty for generated courses,
so tutor misconception tags are dropped today. Root units now carry misconceptions with stable
snake_case ids (`root_units.content.misconceptions[].id`) and every lesson written from a unit is
pinned to it (`concept_unit_pins`). A tutor tag can be resolved as: concept -> pins -> unit ->
misconception id. Not wired yet; it belongs to the layer's step 1.

**Migrations.** `0051_course_brain` is taken by generation (roots, aliases, matches, root units,
sources, pins; new columns on `generated_courses` and `enrollments`). The layer's
`users.learner_profile` migration must be `0052_...` with `down_revision = "0051_course_brain"`,
and bump `schema_revision.py` and `tests/test_quiz_runtime_tables.py`.

## 2. The course brain (`coursegen/brain/`)

| Entry | What it does |
|---|---|
| `route.route(db, catalog, user_id, row, intent)` | called first in `requests.begin` when `settings.course_brain`. Serves an existing course (`row.status = "matched"`) or says why a course must be built, and which root units it uses |
| `route.attach(db, course_id)` | called by `requests.publish`: stamps root, spec, `serve` on a built course |
| `route.granted(db, user_id, course_id)` | `POST /enrollments`: lets a served learner enrol and copies their private overlay |
| `spec.derive / is_private / overlay` | request -> hard spec / private flag / learner-only overlay (code only) |
| `roots.resolve` | any subject -> one root, created on demand; synonyms folded; merges redirect |
| `units.ensure / load / block / pin / quarantine` | root material: research once, load for prompts, record which revision a lesson used, withdraw |
| `researcher.run_research` | job kind `research` (course id `root:<root>`, target unit key): sources, `extractor` call, code validation, new unit revision |

Adding a hard requirement (something that changes the lessons): add a field to `CourseSpec`, derive
it in `spec.derive`, compare it in `route.compatible`. Adding something only one learner's sessions
need: put it in `spec.overlay`, never in `CourseSpec`.

## 3. Generation jobs

| Kind | Course id | Target | Notes |
|---|---|---|---|
| `outline` | the course | "" | waits (state `queued`, stage `waiting`, no attempt counted) up to `UNIT_WAIT_SECONDS` while its root units are researched, then plans from `Brief.subject_material` |
| `research` | `root:<root id>` | unit key | priority 0, one open job per unit (unique open-job index) |
| `package` | the course | concept id | loads root units of `Brief.units`, pins them, then the learner hook |
