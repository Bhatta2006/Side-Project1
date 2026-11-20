# Course generation: plug points for other modules

The one page to read before plugging a module into course generation. Kept current by whoever
changes a plug point. Last updated 2026-11-20 (course brain, root units, learner-layer hook).

Related: `course-brain-plan.md` (why the brain exists), `lesson0-generation-plan.md` (onboarding
to generation), `onboarding-handoff.md` (the onboarding contract).

## 1. The learner layer (`socrat/learner/`, built in parallel)

The layer has landed as `services/api/src/socrat/learner.py`; its side of the contract, the
brief's keys and the preference sources are in `learner-memory.md`. The brief keeps itself under
3,500 characters and holds no `<` or `>` in any value, so `lesson_block` never cuts it mid-JSON.

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
| `lesson_block(db, course_id, now)` | `jobs.run_package`, after the pedagogical-strategy block and root material, only when `settings.gen_learner_brief` (off by default) | the course is **private** to one learner (owner set, `serve != "shared"`, not public) and that learner has an enrollment in it | built; tested with a fake layer (`tests/test_brain_units.py::test_learner_layer_shapes_private_lessons_only`) and with the real layer (`tests/test_learner_generation.py`) |
| `brief_for(db, enrollment, now, purpose)` | any generation code that needs the raw dict | as above | built |
| `outline_block(db, user_id, request_id, now)` | `jobs.run_outline`, after the reuse check and before the stylist and architect, only when `gen_learner_brief` | the request builds a course only its maker reads (`builds_private`: no brain decision, or `private_new`); never an admin brief or a shareable build | **built** (2026-11-20): `brief_for_user(..., "outline")` -> `learner.user_brief`. Goes into `Brief.learner_brief`, which the architect and critic read (`brief_text`) and which is **never stored** with the course. Test: `tests/test_learner_hooks.py` |
| first lessons before the owner enrols | `lesson_block` / `quiz_block`, when `owner_enrollment` is None | private course | **built**: falls back to `user_brief(db, owner, now, purpose)` |
| `quiz_block(db, course_id, now)` | `jobs.run_package`, added to the **quiz** prompt only, when `gen_learner_brief` | private course | **built**: `brief(..., "quiz")` (or `user_brief` before enrolment) |
| misconception tags on quiz options | `jobs.run_package` (quiz prompt), `learn/quizzes.answer/finish` (grading) | any course written from root units (shared too: the ids are the unit's, not the learner's) | **built**: the quiz prompt lists the pinned units' misconception ids (`units.misconceptions`, `pkg.tags_block`); a wrong option may carry one (`"misconceptions"` aligned with options, or `"misconception"` on a marked option); `pkg.keep_tags` drops any id not in those units; `QuizItem.misconceptions` drops tags that do not line up or sit on the answer. A learner who picks a tagged option gets `details["misconception"]` on the concept's quiz evidence (the most frequent tag), which the layer's snapshot already reads |

**Lesson 0 plan, next to the layer.** `coursegen/learner_plan.py` (flag `gen_learner_plan`) carries what the
learner *said* in Lesson 0 (their words, explicit asks, door, calibration) in `Brief.plan`; the layer carries
what they *do*. Both reach a private course's prompts, each as its own marked block, and both stop at the same
`private_owner` check. See `lesson0-generation-plan.md` (implementation status).

**Privacy rule (enforced in one place, `private_owner`).** A learner's brief may shape the lessons
of a course only that learner reads. Shared courses (served by the brain to other learners, or
shared publicly by their maker) are never written from one learner's brief. For those, the brief
shapes that learner's own sessions: planner order, quiz selection, tutor. That is the layer's
side, read from `Enrollment.learner_plan` and the layer's own data.

Two code guards back this up (`coursegen/brain/privacy.py`): a shareable course is generated from
`shared_intent(intent)` (Lesson 0 door and gaps sentences, age, deadline and hours removed), and
`leaks(db, course_id)` keeps a course private when its maker's own words (8-word runs), email or
full name appear in anything learners read. If the layer ever adds text to a shared course's
prompts, `leaks` will catch a copy of the maker's words, but the rule above is the real guard.

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
pinned to it (`concept_unit_pins`). **Wired (layer):** `learner.misconceptions_for(db,
"course:concept")` resolves concept -> pins -> units -> `{id: belief}`; the tutor sees those ids
for the lesson in scope and `record_observation` stores one only when it is in that list (or the
catalog's). For the quiz builder: give generated distractors these same ids in
`details["misconception"]` when grading, and they flow into the learner's brief.

**Migrations.** `0051_course_brain` is generation's (roots, aliases, matches, root units,
sources, pins; new columns on `generated_courses` and `enrollments`). `0052_learner_profile` is
the layer's (`users.learner_profile`, done). Generation's next one is `0053`, with
`down_revision = "0052_learner_profile"`; bump `schema_revision.py` and
`tests/test_quiz_runtime_tables.py`.

## 2. The course brain (`coursegen/brain/`)

| Entry | What it does |
|---|---|
| `route.route(db, catalog, user_id, row, intent)` | called first in `requests.begin` when `settings.course_brain`. Serves an existing course (`row.status = "matched"`) or says why a course must be built, and which root units it uses |
| `route.attach(db, course_id)` | called by `requests.publish`: stamps root, spec, `serve` on a built course |
| `route.granted(db, user_id, course_id)` | `POST /enrollments`: lets a served learner enrol and copies their private overlay |
| `route.family(db, spec)` / `route.joined` | a shareable course is built under `<topic>-<spec key[:8]>` (`-vN`); a request with the same spec while it is being written is `joined` instead of building again |
| `privacy.shared_intent / leaks` | learner-only parts removed from a shareable course's request; leakage gate run at publish and before serving |
| `units.correct(db, base, unit_id, reason)` | withdraw a unit revision, research a corrected one, rewrite every live lesson pinned to it |
| `GET /api/v1/admin/brain/roots`, `/units`, `/matches/{request_id}`; `POST /units/{id}/correct` | owner views and the correction action (`brain/routes.py`) |
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
| `package` | the course | concept id | waits like `outline` while a unit it rests on is being re-researched after a correction (a routine refresh is not waited for); loads root units of `Brief.units`, pins them (replacing a pin to an older revision), then the learner hook |
