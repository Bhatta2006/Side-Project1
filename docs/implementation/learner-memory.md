# Learner memory: how to read it, how to plug a feature into it

Living document. **Update it in the same change** whenever you add a consumer, a writer, a
preference key or a store. Code: `services/api/src/socrat/learner.py` (read side) and
`services/api/src/socrat/learner_profile.py` (write side, routes). Tests:
`services/api/tests/test_learner_snapshot.py`, `test_learner_generation.py`,
`test_learner_profile.py`.

Generation's side of the contract is `docs/implementation/generation-plug-points.md` (owned by
course generation). This file is the layer's side. Keep the two in step.

Status log (newest first):

| Date | Step | What changed |
|---|---|---|
| 2026-11-20 | G (generation) | Generation's hooks built: `outline_block` (outline of a private course, through `user_brief`), first-lesson fallback to `user_brief` before the owner enrols, `quiz_block` (quiz prompt only), and quiz options tagged with root-unit misconception ids, graded into `details["misconception"]`. All behind `SOCRAT_GEN_LEARNER_BRIEF` except the tags (they hold no learner data). Tests: `test_learner_hooks.py`. |
| 2026-11-20 | 3, 4, 5 | Rebased on generation's `f56d0ae`. **Step 3:** `users.learner_profile` (migration `0052_learner_profile`), `learner_profile.set_pref` / `undo` / `seed_from_lesson0` (called at the Lesson 0 claim), learner routes under `/api/v1/learner/profile`. **Step 4:** preferences read from behaviour (`learner.observed`), and the tutor tool `suggest_preference`, which only adds a pending suggestion the learner accepts or declines. **Misconceptions** of generated lessons resolve through unit pins (`learner.misconceptions_for`); the tutor sees them and may tag one. **Step 5 (light):** `learner.user_brief` for work with no enrollment (outline, first lessons) lists what the learner already shows in other courses. The writes, routes and tutor tool are behind `SOCRAT_LEARNER_PROFILE` (off). |
| 2026-11-20 | 2 of 5 | Rebased on generation's course brain (`0051_course_brain`). The layer now answers generation's hook (`coursegen/brain/learner.py`): `snapshot(db, enrollment, now)`, `brief(snap, purpose, budget)`. Our own generation hook was dropped in favour of theirs (their privacy rule also covers brain-shared courses). The call in `run_package` is behind `SOCRAT_GEN_LEARNER_BRIEF` (off). The served learner's overlay (`enrollments.learner_plan`) is read as onboarding preferences. |
| 2026-11-20 | 1 of 5 | `learner.snapshot` / `brief` / `render` added, reading existing data only (no migration). The tutor now reads through it (`assistant/service.learner_sections`); `learn.memory.tutor_block` removed. |

---

## 1. The idea in one paragraph

Socrat remembers a learner in several stores (section 4). No feature should read those stores
directly. Every feature reads **one object**, `learner.snapshot(...)`, and when it needs to
put the learner into a model prompt, it builds a **brief** (`learner.brief(...)`) and, unless a
hook wraps it already, renders it (`learner.render(...)`). Writes go through the few existing
writers only (section 5). Models explain; code decides what the learner knows.

## 2. Read API (stable: `learner-snapshot/1`, `learner-brief/1`)

```python
from socrat import learner

snap = learner.snapshot(db, enrollment, now)                 # read-only
b = learner.brief(snap, "module", concepts=["course:next"])  # JSON-safe dict, <= budget chars
prompt_block = learner.render(b)                             # <learner_brief>…</learner_brief>
```

`snapshot(db, enrollment, now, *, catalog=None, user=None, states=None)`: the three positional
arguments are what generation calls. A request handler that already has the catalog, the user or
`learn.states_for(...)` passes them as keywords to save the lookups (the tutor does).

No enrollment yet (a new course's outline, its first lessons before the learner enrols)?

```python
b = learner.user_brief(db, user_id, now, purpose="outline")   # {} for an unknown user
# {schema, purpose, delivery, shown_elsewhere, other_courses, starting_sample?}
```

`delivery` is the person's preferences (stored ones and strictness); `shown_elsewhere` is the
titles of concepts they have mastered with evidence in any of their courses; `starting_sample`
is their latest calibrated Lesson 0. Same size limit and `<`/`>` guarantee as `brief`.

Misconceptions of a generated lesson: `learner.misconceptions_for(db, "course:concept")` gives
`{id: belief}` from the root units the lesson was written from (`concept_unit_pins`).

### `Snapshot`

| Field | What it is | Built from |
|---|---|---|
| `concepts[c]` | a `ConceptView` per concept with a state (enrolment seeds every course concept) | mastery state + evidence |
| `.band` | `not_started / needs_practice / developing / likely_known / strong` | `mastery.model.band` |
| `.stage` | `unknown / emerging / developing / proficient / demonstrated` | `mastery.evidence.summarise` |
| `.mastery`, `.confidence` | estimate discounted when a review is overdue; how much evidence stands behind it | `ConceptState` |
| `.due` | a spaced review is due now | `ConceptState.due` |
| `.attempts`, `.hint_dependence` | scored attempts; share of successes that needed help | `adaptive.profile` |
| `.misconceptions` | unresolved tag -> misses (cleared by a later correct answer) | `evidence.details["misconception"]` |
| `.stuck` | plain summary when the stuck detector fires | `adaptive.stuck` |
| `.feel` | `hard` / `easy` pace for this concept, learner's override over the mentor's | `enrollments.adaptive` |
| `prerequisites[c]` | direct prerequisites of every concept of the course | catalog |
| `prefs[key]` | `Pref(value, source)`, resolved (section 3) | several, see 3 |
| `calibration` | the Lesson 0 sample: own profile, else the served overlay's, else None | `onboarding.profile_for`, `enrollments.learner_plan` |
| `noticed` | short code-built lines on how lessons were read (empty while `SOCRAT_LESSON_SIGNALS` is off) | `learn.memory.remembered` |
| `beliefs` | misconception id -> belief, for ids this learner has missed in generated lessons | `misconceptions_for` |
| `states`, `skill`, `stuck` | the raw parts, for a consumer needing more than the views | as named |

### `brief(snap, purpose="module", budget=3500, concepts=None, limit=8)`

- `purpose`: `module | quiz | tutor | outline` (`learner.PURPOSES`); anything else is refused. It is
  recorded in the brief; the content is the same for every purpose today.
- `budget`: the most characters the serialised brief may take. Lists are shortened first, then
  `noticed`, `pace`, `starting_sample`, `review`, `skip` are dropped in that order. Generation
  cuts at 4,000 characters, so the default keeps the JSON whole.
- `concepts`: the scope, usually what you are about to write or test. Their direct prerequisites
  are added. `None` = whole course.
- **No string in a brief holds `<` or `>`** (replaced by `‹ ›`), because generation's hook wraps
  the raw JSON in a tag without escaping, and `delivery.analogy_domain` is learner-typed.

```json
{
  "schema": "learner-brief/1",
  "purpose": "module",
  "skip":           ["titles already strong: skip or compress"],
  "patch_first":    [{"concept": "...", "title": "...", "why": "stuck summary, or band + stage"}],
  "misconceptions": [{"concept": "...", "tag": "...", "misses": 3, "belief": "when known"}],
  "review":         ["titles with a review due: slip one question in"],
  "pace":           {"title": "hard | easy"},
  "delivery":       {"analogy_domain": "...", "tone": "...", "strictness": "...", "...": "..."},
  "noticed":        ["Asked for a simpler explanation of X 3 times."],
  "starting_sample": {"only while there are no scored attempts: the Lesson 0 prior"}
}
```

## 3. Preferences: keys, sources, precedence

Precedence, strongest first: **`learner` > `mentor` > `observed` > `onboarding` > `default`**
(`learner.SOURCES`). What the learner chose always wins. Empty values are not preferences.

Three kinds of input feed the same resolution:

- **Stored** on `users.learner_profile` (step 3), with the source that wrote them: the learner
  (routes, accepted suggestions), Lesson 0 (`seed_from_lesson0`, source `onboarding`), and later
  the mentor. They follow the person into every course.
- **Observed**, computed by code on every snapshot and never stored (`learner.observed`):
  `explanation_length` from "simpler"/"deeper" taps on at least 2 lessons, `pace` from the median
  time against plan over at least 3 concepts. Being recomputed, they need no undo, and a stored
  learner choice always beats them.
- **Read from other stores**: the rows below.

| Key | Sources today | Notes |
|---|---|---|
| `strictness` | learner (`users.learning_mode`), default `balanced` | quiz/tutor strictness |
| `path_style` | learner (`enrollments.adaptive["style"]`), default `balanced` | planner |
| `learning_style` | learner (`enrollments.adaptive["learning_style"]`, a StyleSpec dict) | |
| `daily_minutes` | learner (`enrollments.minutes_per_day`) | what they planned (rounded up to 15/20/30/...); a Lesson 0 course also has the true session length in `enrollments.goal.session_minutes` (generation, 2026-11-20), which the planner packs to |
| `actual_daily_minutes` | observed (planned x adherence over 28 days) | what they really do |
| `review_spacing` | observed (`adaptive.profile.review_scale`) | personal forgetting rate |
| `age`, `register`, `approach`, `balance` | learner (validated `Intent` of a course they made) | never another learner's picks |
| `course_mode` | onboarding (`learning_mode`; overlay `mode`) | sprint / builder / explorer |
| `analogy_domain` | onboarding (`primary_analogy_domain`; overlay `door`) | **untrusted text** |
| `tone` | onboarding (`preferred_tone`; overlay `tone`) | derived from mode |
| `explanation_length` | onboarding (`max_explanation_length`); observed (taps) | from minutes, then behaviour |
| `friction_limit` | onboarding (`friction_limit_attempts`) | when the tutor should step in |
| `pace` | onboarding (`pace_level`; overlay `calibration.pace_level`); observed (speed) | a prior, then behaviour |

Where onboarding values come from:

- **The learner made the course** (owner): the validated intent and the Lesson 0 profile of
  their own request (`learner._origin`). A profile whose `meta.schema` is not the current
  `PROFILE_SCHEMA` is ignored: when onboarding bumps the schema, update `learner.ONBOARDING`.
- **The brain served them someone else's course**: `enrollments.learner_plan`, the per-learner
  overlay generation copies at enrolment (`coursegen/brain/spec.overlay`), mapped by
  `learner.PLAN`. When generation adds a field to the overlay, add it to `PLAN` here.

Both present: the learner's own profile wins. Any key in `learner_profile.WRITABLE` can also be
stored (learner, mentor, observed or onboarding) and then competes by source as above.

## 4. Where the memory is stored

| Store | Holds | Only writer |
|---|---|---|
| `evidence` (append-only) | every scored attempt: kind, score, hint level, time, misconception | `learn.service.record_evidence` |
| `concept_states` | mastery per enrollment and concept (rebuildable from `evidence`) | `record_evidence` |
| `activity_records` `signal:*` | reading counters (simpler, deeper, reread, question, visual) | `learn.memory.note` |
| `enrollments.adaptive` | path style, overrides, mentor moves + undo log, learning style, streak goal | accepted proposals, mentor, settings routes |
| `enrollments.learner_plan` | served learner's overlay: request, minutes, level, deadline, mode, door, tone, calibration | `POST /enrollments` (generation) |
| `users.learner_profile` | `learner-profile/1`: stored preferences with source and reason, an undo log (60), the tutor's pending suggestions (5) | `learner_profile.set_pref` / `undo` / `suggest` / `decide` / `seed_from_lesson0` |
| `users.learning_mode` | strictness | settings |
| `learning_requests.intent` | the learner's validated picks for a course they made | course request |
| `onboarding_drafts.profile` | Lesson 0 profile (read via `onboarding.profile_for` only) | onboarding claim |

Mastery is per enrollment: a second course starts empty (see step 5).

## 5. Rules for writers (do not break these)

1. **Only `record_evidence` moves mastery.** No feature updates `concept_states` itself.
2. **Signals never score.** Counters (`learn.memory.note`) can make the stuck detector look; they
   cannot change mastery, progress or streaks.
3. **A model never writes memory directly.** It proposes; code validates and writes. The pattern
   to copy is the tutor tool `record_observation` (`assistant/tools.py`): validated concept,
   weight capped (`tutor` 0.15), can only flag a gap (score <= 0.5), rate-limited per day.
4. **Lesson 0 is a prior.** It never writes evidence and is replaced by real behaviour.
5. **Never label the learner** (no "IQ", "grit"). Show bands and stages, not fake-precise numbers.
6. **Preferences are validated and owned.** Only keys in `learner_profile.WRITABLE`, only allowed
   values (no `<` or `>` in text), only the `WRITERS` sources. Keys another store owns
   (strictness, minutes) are not writable here. A weaker source never overwrites a stronger one,
   and every write is logged with a reason and can be undone.

### Write API (`socrat.learner_profile`)

```python
set_pref(user, key, value, source, why) -> entry | None   # None: a stronger source holds it
undo(user, entry_id) -> entry | None                      # not when a later write stands on it
suggest(user, key, value, why) -> item                    # a model's: pending, applies nothing
decide(user, suggestion_id, accept) -> item | None        # the learner's answer
seed_from_lesson0(user, lesson0_profile) -> [entries]     # at the Lesson 0 claim
```

Routes (404 while `SOCRAT_LEARNER_PROFILE` is off): `GET /api/v1/learner/profile` (preferences in
force with their source, pending suggestions, history), `PUT /api/v1/learner/profile/{key}`
`{"value": ...}` (the learner's choice), `POST /api/v1/learner/profile/undo/{entry_id}`,
`POST /api/v1/learner/profile/suggestions/{id}` `{"accept": bool}`. No web screen yet.

## 6. Recipes: plugging a feature in

**Course generation: wired through generation's hook.** Generation calls this layer only
through `coursegen/brain/learner.py` (theirs). That module owns the privacy rule
(`private_owner`: owner set, not `serve == "shared"`, not public), picks the owner's enrollment,
calls `brief(snapshot(db, enrollment, now), "module")`, and wraps the JSON in
`<learner_brief>` with its own instruction. `run_package` calls `lesson_block` only when
`settings.gen_learner_brief` is on. Hooks still to build are listed in
`generation-plug-points.md` (outline for a new private course, quiz generation).

Do not import `socrat.learner` from anywhere else in `coursegen`: add a function to their hook.

**Quizzes.** `brief(snap, "quiz", concepts=quiz_concepts)`: target `misconceptions` with
distractors, weight `patch_first`, include `review`. Grade answers with `record_evidence` and
put the distractor's tag in `details["misconception"]` so it shows up here next time.

**Tutor.** Already wired: `learner_sections` builds the snapshot once and `adaptive_section`
reads `snap.skill` / `snap.stuck`. On a lesson, the tutor is shown `known_misconceptions` (ids
and beliefs from `misconceptions_for`) and may pass one to `record_observation(misconception=...)`;
an id outside that list (or the catalog's) is ignored. With `SOCRAT_LEARNER_PROFILE` on, it also
has `suggest_preference`, which only adds a pending suggestion. A new tutor section reads from
`snap`, never from the stores.

**A new preference.** Readable only: add one `offer(key, source, value)` line in `learner._prefs`
and a row in section 3. Writable: also add its validator to `learner_profile.WRITABLE` (and, if a
model may suggest it, to the `suggest_preference` tool's enum). Read from behaviour: add a rule to
`learner.observed`.

**The mentor writing a preference.** `set_pref(user, key, value, "mentor", why)`: it can never
overwrite the learner's own choice, and the learner can undo it from their history.

**A new signal.** Add the kind to `learn.memory.COUNTERS` / `Signal`, a line in `remembered`, and
(if it should count as a stuck sign) a rule in `adaptive/stuck.py`.

## 7. Known gaps (verified 2026-11-20)

- **Generated quizzes tag misconceptions only for lessons written from root units** (the ids
  come from the pinned units). Quizzes written before this change carry no tags.
- **Lessons without a pin** (written before the course brain, or with no root units) have no
  known misconceptions, so the tutor's tag for them is still dropped.
- **Lesson 0 `detected_gaps` are model-written labels**, not concept ids. `brief` passes them
  through in `starting_sample` only; nothing maps them to concepts yet.
- **No web screen** for the learner profile, its history or pending suggestions; the API is there.
- **Mastery itself does not carry over between courses.** `user_brief.shown_elsewhere` tells an
  outline what the learner already shows, by title; a new course's concepts still start empty.
- **A course shared later keeps lessons fitted to its owner.** Lessons already written while it
  was private are not rewritten when it becomes shared.
- **The strategist still gets a fixed `"unknown"` stage** in `run_package`. Passing the learner's
  stage on the concept (`snap.concepts[c].stage`) would need a second function in generation's
  hook; it matters only for rewritten concepts, since a planned one has no evidence yet.
- Not verified: behaviour with a live model, and cost of `snapshot` on a large course (it reads
  all of the enrollment's evidence once per call, like the tutor already did).

## 8. Roadmap

| Step | What | Status |
|---|---|---|
| 1 | `snapshot` + `brief` + `render` over existing data; tutor moved onto it | **done** |
| 2 | Lessons of a private course written from its learner's brief, through generation's hook, flag `gen_learner_brief` | **done**, off by default; not run against a live model |
| 3 | `users.learner_profile` (`0052_learner_profile`), validated writer with sources, undo log, Lesson 0 seeding at claim, learner routes | **done**, behind `SOCRAT_LEARNER_PROFILE`; no web screen |
| 4 | Preferences read from behaviour (`observed`); tutor suggestions that apply only when the learner accepts | **done**. A suggestion is confirmed by the learner, not by signals: signals already move the observed value on their own |
| 4b | Misconceptions of generated lessons resolved through unit pins; the tutor sees and tags them | **done** |
| 5 | What carries between courses: `user_brief.shown_elsewhere` for outlines | **light version done**; mastery transfer between courses (matching concepts) waits until learners take second courses |
| G | Generation's hooks: outline (`brief_for_user`), first-lessons fallback, quiz builder tags | **done** (generation), behind `gen_learner_brief`; not run against a live model |
