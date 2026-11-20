# Learner memory: how to read it, how to plug a feature into it

Living document. **Update it in the same change** whenever you add a consumer, a writer, a
preference key or a store. Code: `services/api/src/socrat/learner.py`. Tests:
`services/api/tests/test_learner_snapshot.py`.

Status log (newest first):

| Date | Step | What changed |
|---|---|---|
| 2026-11-20 | 1 of 5 | `learner.snapshot` / `brief` / `render` added, reading existing data only (no migration). The tutor now reads through it (`assistant/service.learner_sections`); `learn.memory.tutor_block` removed. |

---

## 1. The idea in one paragraph

Socrat remembers a learner in several stores (section 4). No feature should read those stores
directly. Every feature reads **one object**, `learner.snapshot(...)`, and when it needs to
put the learner into a model prompt, it builds a **brief** (`learner.brief(...)`) and renders it
(`learner.render(...)`). Writes go through the few existing writers only (section 5). Models
explain; code decides what the learner knows.

## 2. Read API (stable: `learner-snapshot/1`, `learner-brief/1`)

```python
from socrat import learner

snap = learner.snapshot(db, catalog, user, enrollment, now)          # read-only
b = learner.brief(snap, concepts=["course:next-a", "course:next-b"]) # JSON-safe dict
prompt_block = learner.render(b)                                     # <learner_brief>…</learner_brief>
```

Pass `states=` to `snapshot` if you already loaded `learn.states_for(...)`.

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
| `calibration` | the Lesson 0 sample (`lesson0-profile/1` `calibration`), or None | `onboarding.profile_for` |
| `noticed` | short code-built lines on how lessons were read (empty while `SOCRAT_LESSON_SIGNALS` is off) | `learn.memory.remembered` |
| `states`, `skill`, `stuck` | the raw parts, for a consumer needing more than the views | as named |

### `brief(snap, concepts=None, limit=8)`

`concepts` is the scope, usually the concepts you are about to generate or test. Their direct
prerequisites are added automatically. `None` = whole course.

```json
{
  "schema": "learner-brief/1",
  "known":          ["titles already strong: skip or compress"],
  "patch_first":    [{"concept": "...", "title": "...", "why": "stuck summary, or band + stage"}],
  "misconceptions": [{"concept": "...", "tag": "...", "misses": 3}],
  "review":         ["titles with a review due: slip one question in"],
  "pace":           {"title": "hard | easy"},
  "delivery":       {"analogy_domain": "...", "tone": "...", "strictness": "...", "...": "..."},
  "noticed":        ["Asked for a simpler explanation of X 3 times."],
  "starting_sample": {"only while there are no scored attempts: the Lesson 0 prior"}
}
```

`render` labels the block as data and escapes `<`, because `delivery.analogy_domain` can be
learner-typed and gap labels are model-written.

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
| `course_mode` | onboarding (`learning_mode`: sprint / builder / explorer) | |
| `analogy_domain` | onboarding (`primary_analogy_domain`) | **untrusted text** |
| `tone`, `explanation_length` | onboarding | derived from mode/minutes |
| `friction_limit` | onboarding (`friction_limit_attempts`) | when the tutor should step in |
| `pace` | onboarding (`pace_level`) | one data point, a prior |

The intent and the Lesson 0 profile are read only when the learner **owns** the generated course
(`learner._origin`). A Lesson 0 profile whose `meta.schema` is not the current `PROFILE_SCHEMA`
is ignored, not guessed at: when onboarding bumps the schema, update `learner.ONBOARDING`.

## 4. Where the memory is stored (nothing new yet)

| Store | Holds | Only writer |
|---|---|---|
| `evidence` (append-only) | every scored attempt: kind, score, hint level, time, misconception | `learn.service.record_evidence` |
| `concept_states` | mastery per enrollment and concept (rebuildable from `evidence`) | `record_evidence` |
| `activity_records` `signal:*` | reading counters (simpler, deeper, reread, question, visual) | `learn.memory.note` |
| `enrollments.adaptive` | path style, overrides, mentor moves + undo log, learning style, streak goal | accepted proposals, mentor, settings routes |
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

**Course generation (lazy next module).** In the job that writes module N+1:

```python
snap = learner.snapshot(db, catalog, user, enrollment, now)
block = learner.render(learner.brief(snap, concepts=next_module_concept_ids))
# add `block` to the architect/author prompt; tell the model: skip `known`,
# open with `patch_first` and `misconceptions`, add one question per `review`,
# use `delivery` for analogy, tone and length.
```

The concept ids of module N+1 must exist in the catalog for prerequisites to resolve. Before the
first module (no evidence), the brief carries `starting_sample` from Lesson 0.

**Quizzes.** `brief(snap, concepts=quiz_concepts)`: target `misconceptions` with distractors,
weight `patch_first`, include `review`. Grade answers with `record_evidence` and put the
distractor's tag in `details["misconception"]` so it shows up here next time.

**Tutor.** Already wired: `learner_sections` builds the snapshot once and `adaptive_section`
reads `snap.skill` / `snap.stuck`. A new tutor section reads from `snap`, never from the stores.

**A new preference.** Add one `offer(key, source, value)` line in `learner._prefs` and a row in
section 3. To let something *write* a preference, that is step 3 below.

**A new signal.** Add the kind to `learn.memory.COUNTERS` / `Signal`, a line in `remembered`, and
(if it should count as a stuck sign) a rule in `adaptive/stuck.py`.

## 7. Known gaps (verified 2026-11-20)

- **Misconception tags are dropped in generated courses.** The tutor's `record_observation` only
  tags a misconception when it is in `catalog.misconceptions`, which comes from
  `content/atoms/misconceptions.yaml`. That file no longer exists, so the set is empty. Generated
  concepts carry free-text `Outline.misconceptions` instead. Fix together with generation: give
  generated misconceptions stable slugs and accept those.
- **Lesson 0 `detected_gaps` are model-written labels**, not concept ids. `brief` passes them
  through in `starting_sample` only; nothing maps them to concepts yet.
- **Nothing carries over between courses** (mastery is per enrollment).
- Not verified: behaviour with a live model, and cost of `snapshot` on a large course (it reads
  all of the enrollment's evidence once per call, like the tutor already did).

## 8. Roadmap

| Step | What | Status |
|---|---|---|
| 1 | `snapshot` + `brief` + `render` over existing data; tutor moved onto it | **done** |
| 2 | Wire `brief(concepts=next module)` into lazy module generation | waits on the generation entry point |
| 3 | `users.learner_profile` (JSON, migration coordinated with onboarding) + `set_pref(db, user, key, value, source, why)` with an undo log; seed from the Lesson 0 profile at claim. `_prefs` gains one `offer` per stored key | not started |
| 4 | Tutor proposes preference changes (fixed set of allowed values), confirmed by signals (fewer "simpler" taps, better practice) before they apply | not started |
| 5 | Matching concepts across courses, so a second course starts from what is known | only once second courses happen |
