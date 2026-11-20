# Learner memory: how to read it, how to plug a feature into it

Living document. **Update it in the same change** whenever you add a consumer, a writer, a
preference key or a store. Code: `services/api/src/socrat/learner.py`. Tests:
`services/api/tests/test_learner_snapshot.py`, `test_learner_generation.py`.

Generation's side of the contract is `docs/implementation/generation-plug-points.md` (owned by
course generation). This file is the layer's side. Keep the two in step.

Status log (newest first):

| Date | Step | What changed |
|---|---|---|
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
| `states`, `skill`, `stuck` | the raw parts, for a consumer needing more than the views | as named |

### `brief(snap, purpose="module", budget=3500, concepts=None, limit=8)`

- `purpose`: `module | quiz | tutor` (`learner.PURPOSES`); anything else is refused. It is
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
  "misconceptions": [{"concept": "...", "tag": "...", "misses": 3}],
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

| Key | Sources today | Notes |
|---|---|---|
| `strictness` | learner (`users.learning_mode`), default `balanced` | quiz/tutor strictness |
| `path_style` | learner (`enrollments.adaptive["style"]`), default `balanced` | planner |
| `learning_style` | learner (`enrollments.adaptive["learning_style"]`, a StyleSpec dict) | |
| `daily_minutes` | learner (`enrollments.minutes_per_day`) | what they planned |
| `actual_daily_minutes` | observed (planned x adherence over 28 days) | what they really do |
| `review_spacing` | observed (`adaptive.profile.review_scale`) | personal forgetting rate |
| `age`, `register`, `approach`, `balance` | learner (validated `Intent` of a course they made) | never another learner's picks |
| `course_mode` | onboarding (`learning_mode`; overlay `mode`) | sprint / builder / explorer |
| `analogy_domain` | onboarding (`primary_analogy_domain`; overlay `door`) | **untrusted text** |
| `tone` | onboarding (`preferred_tone`; overlay `tone`) | derived from mode |
| `explanation_length` | onboarding (`max_explanation_length`) | derived from minutes |
| `friction_limit` | onboarding (`friction_limit_attempts`) | when the tutor should step in |
| `pace` | onboarding (`pace_level`; overlay `calibration.pace_level`) | one data point, a prior |

Where onboarding values come from:

- **The learner made the course** (owner): the validated intent and the Lesson 0 profile of
  their own request (`learner._origin`). A profile whose `meta.schema` is not the current
  `PROFILE_SCHEMA` is ignored: when onboarding bumps the schema, update `learner.ONBOARDING`.
- **The brain served them someone else's course**: `enrollments.learner_plan`, the per-learner
  overlay generation copies at enrolment (`coursegen/brain/spec.overlay`), mapped by
  `learner.PLAN`. When generation adds a field to the overlay, add it to `PLAN` here.

Both present: the learner's own profile wins.

## 4. Where the memory is stored (nothing new yet)

| Store | Holds | Only writer |
|---|---|---|
| `evidence` (append-only) | every scored attempt: kind, score, hint level, time, misconception | `learn.service.record_evidence` |
| `concept_states` | mastery per enrollment and concept (rebuildable from `evidence`) | `record_evidence` |
| `activity_records` `signal:*` | reading counters (simpler, deeper, reread, question, visual) | `learn.memory.note` |
| `enrollments.adaptive` | path style, overrides, mentor moves + undo log, learning style, streak goal | accepted proposals, mentor, settings routes |
| `enrollments.learner_plan` | served learner's overlay: request, minutes, level, deadline, mode, door, tone, calibration | `POST /enrollments` (generation) |
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
reads `snap.skill` / `snap.stuck`. A new tutor section reads from `snap`, never from the stores.

**A new preference.** Add one `offer(key, source, value)` line in `learner._prefs` and a row in
section 3. To let something *write* a preference, that is step 3 below.

**A new signal.** Add the kind to `learn.memory.COUNTERS` / `Signal`, a line in `remembered`, and
(if it should count as a stuck sign) a rule in `adaptive/stuck.py`.

## 7. Known gaps (verified 2026-11-20)

- **Misconception tags are dropped in generated courses.** The tutor's `record_observation` only
  tags a misconception when it is in `catalog.misconceptions` (from a `misconceptions.yaml`
  that no longer exists). Generation now stores root units with stable misconception ids
  (`root_units.content.misconceptions[].id`) and pins each lesson to its units
  (`concept_unit_pins`), so concept -> pins -> unit -> ids can resolve a tag. Not wired yet.
- **Lesson 0 `detected_gaps` are model-written labels**, not concept ids. `brief` passes them
  through in `starting_sample` only; nothing maps them to concepts yet.
- **Nothing carries over between courses** (mastery is per enrollment).
- **Lessons written before the owner enrols get no brief.** The first lessons are queued when the
  plan is saved or published, before `POST /enrollments`, so the hook finds no enrollment. They
  still get the Lesson 0 details through the course brief's prose (`style_request`, `notes`).
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
| 3 | `users.learner_profile` (JSON, migration `0052`, `down_revision = "0051_course_brain"`) + `set_pref(db, user, key, value, source, why)` with an undo log; seed from the Lesson 0 profile at claim. `_prefs` gains one `offer` per stored key | not started |
| 4 | Tutor proposes preference changes (fixed set of allowed values), confirmed by signals (fewer "simpler" taps, better practice) before they apply | not started |
| 5 | Matching concepts across courses, so a second course starts from what is known | only once second courses happen |
