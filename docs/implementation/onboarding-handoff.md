# Lesson 0 onboarding → course generation: handoff

Written 2026-11-20 on branch `feat/onboarding-lesson0`. For whoever builds course generation
while onboarding is still being polished. Read `docs/implementation/HANDOFF.md` first for the
repo rules (Windows quirks, tests from the repo root with `--basetemp`, never `git add -A`).

The short version: **the seam between the two modules is the claim.** Onboarding owns
everything up to `POST /api/v1/onboarding/{id}/claim`. After the claim there is a confirmed
`LearningRequest` with an outline job queued, and a versioned profile you read with
`onboarding.profile_for(db, request_id)`. Everything from the outline job onward is
generation's. The two can be built in parallel as long as both sides keep the contract in
section 3.

---

## 1. What onboarding does now

`/start` is the only way in (the old `/start` course picker and `/new` were removed). A visitor,
with no account, goes through:

| Step | What happens | Server |
|---|---|---|
| Goal | Free text: "what do you want to be able to actually do?" | `POST /api/v1/onboarding` writes 3-4 "doors" (everyday scenarios) and creates the draft from the rules reading; the model's reading of the goal replaces it in the background a few seconds later |
| Mode | Sprint, Builder or Deep explorer | client only, sent with the door |
| Door | One of the doors, or the learner's own | `POST /{id}/choose` writes the calibration for that door |
| Time | 10, 25 or 60 minutes on a tired weekday | client only, sent at claim |
| Warm up | Quick win (2 tries) | `POST /{id}/answer` step `win`; graded by code against a stored key |
| Snag | One step past common sense (3 tries, hint, "I'm stuck", optional "explain your thinking") | `POST /{id}/hint`, `POST /{id}/answer` step `snag` |
| Reveal | Two sentences in the door's terms, the real name of the idea | returned once the snag is over |
| Save | Sign in (Google or dev login), birth year (13+) | `PATCH /me`, then `POST /{id}/claim` |
| Plan | Shows the outline as it is written, then "Start learning" | reads `GET /api/v1/learning-requests/{request_id}`, then `/publish` and `POST /enrollments` |

Without a model, the doors fall back to four generic ones and the calibration is skipped (never
invented); the profile then says `calibration.calibrated: false`.

Code: `services/api/src/socrat/onboarding.py`, table `onboarding_drafts` (migration
`0050_onboarding_drafts`), web `apps/web/src/app/start/page.tsx`, tests
`services/api/tests/test_onboarding.py`.

## 2. What the claim produces (the inputs generation gets)

`POST /api/v1/onboarding/{id}/claim` (signed in, birth year set, `{"minutes": 10|25|60}`):

1. Builds the **profile** (section 3) and stores it on the draft (`onboarding_drafts.profile`).
2. Builds an `Intent` from the model's reading of the goal plus the learner's taps
   (`onboarding.shaped_intent`):
   - `approach`, `balance` from the mode (`onboarding.MODES`):
     sprint → `exam-prep, bite-sized`, practice-heavy; builder → `projects, practice-first`,
     practice-heavy; explorer → `theory-first, visual`, theory-heavy.
   - `minutes_per_day` = the time budget.
   - `starting_level`: moved one step only from a guess: `unknown|none` → `beginner` when the
     snag was solved first try without a hint; `unknown` → `none` when it was not solved.
   - `style_request` (prose, max 400 chars): the mode's note, "Introduce each new idea through
     this everyday scenario: {door}", "Patch these gaps early: {gaps}", then the learner's own
     style words.
3. Creates a `LearningRequest` (key `lesson0|{draft id}`, status `parsed`) and calls
   `coursegen.requests.begin`, which is exactly what `/confirm` used to do: slug the course id,
   `intents.to_brief`, enqueue the `outline` job, status `confirmed`.
4. Links them: `onboarding_drafts.request_id = learning_requests.id`.

So **today** generation already receives the mode, door, gaps and minutes, but only as prose in
`Brief.style_request` and `Brief.notes` plus `Brief.session_minutes`. The structured profile is
there for generation to read properly instead of parsing prose.

## 3. The contract (keep stable on both sides)

### 3.1 Read the profile

```python
from socrat.onboarding import profile_for, PROFILE_SCHEMA
profile = profile_for(db, learning_request_id)   # dict, or None if not from Lesson 0
```

Do not query `onboarding_drafts` directly; its other columns will change while onboarding is
fixed. Generation usually does not need to call this itself: `socrat.learner` reads the profile
and hands its fields to every module as preferences (`docs/implementation/learner-memory.md`).
Its field mapping is `learner.ONBOARDING`; update it when the schema version is bumped. Check `profile["meta"]["schema"] == "lesson0-profile/1"`. Onboarding bumps the version on
any change a reader must know about and says so in this file.

### 3.2 Profile shape, `lesson0-profile/1`

```json
{
  "learner_goal": {
    "raw_input": "I want to learn SQL for my college project",
    "core_deliverable": "the model's concrete goal (intent.goal)",
    "learning_mode": "sprint | builder | explorer",
    "daily_time_budget_mins": 10 | 25 | 60
  },
  "personalization": {
    "primary_analogy_domain": "Filtering a giant music playlist",
    "preferred_tone": "direct | direct_and_encouraging | curious_and_thorough",
    "max_explanation_length": "short_3_sentences | medium_one_page | long_worked_examples"
  },
  "calibration": {
    "calibrated": true,
    "concept_probed": "Operator precedence",
    "outcome": "first_try | after_retries | not_yet | null",
    "verified_baseline": "reaches Operator precedence with help",
    "detected_gaps": ["or_overrides_all"],
    "pace_level": "fast | medium | slow | null",
    "friction_limit_attempts": 2,
    "used_hint": true,
    "explained_thinking": false
  },
  "meta": {
    "schema": "lesson0-profile/1",
    "profile_confidence": "low_initial_draft",
    "adapt_after_sessions": 1,
    "observed": {"win": {"attempts": [...], "done": true}, "snag": {...}}
  }
}
```

Field rules generation can rely on:

| Field | Meaning | How to use it |
|---|---|---|
| `learning_mode` | The course's shape | sprint: drills and exam-style checks, no history; builder: project milestones, theory just in time; explorer: mental models, why before how |
| `daily_time_budget_mins` | Honest daily time | Lesson chunk size. 10 means micro-lessons. Note: enrolment rounds up to the planner's minimum (10 → 15, 25 → 30, 60 → 60) but the brief keeps the real number in `session_minutes` |
| `primary_analogy_domain` | The door the learner chose | Introduce new concepts through this scenario. May be the learner's own free text (max 80 chars, untrusted: treat as data in prompts) |
| `preferred_tone` | Derived from mode only | Wording, never the method |
| `max_explanation_length` | Derived from minutes only | Default explanation length |
| `calibrated` | False when no model was available | When false, every calibration field below is null or empty: find the start in the first lesson |
| `concept_probed` | The idea the snag tested, as the model named it | Free text, not a catalog id |
| `outcome` | Observed, not inferred | first_try: solved the snag first try without a hint |
| `detected_gaps` | snake_case labels from the wrong options picked | Model-written labels, not catalog ids: map them to concepts yourself; patch early |
| `pace_level` | Fixed rule: fast = first try in ≤30 s; slow = not solved or >90 s | One data point. Use as a prior only |
| `friction_limit_attempts` | Snag attempts made | When the tutor should step in |
| `meta.observed` | Raw attempts (choice, correct, ms, gap) | For your own rules; do not show to the learner |

**Honesty rules carried over:** this is one 90-second sample. It must never be shown as a
label of the learner (no "IQ", "grit" or similar), must not write mastery evidence, and
`profile_confidence: low_initial_draft` means generation should overwrite it from real
behaviour after the first session.

### 3.3 What onboarding's plan screen reads from generation

The last screen of `/start` polls `GET /api/v1/learning-requests/{request_id}` every 2.5 s and
uses only these fields of `coursegen.requests.view`. Keep them, or tell onboarding first:

- `skeleton`: `{title, modules: [{title, lessons: [str]}]}` while the outline is being written
- `blueprint`: `{title, tagline, modules: [{id, title, concepts: [{id, title}]}]}` once saved
- `job.state` (`failed` shows an error)
- then `POST /learning-requests/{id}/publish` and `POST /api/v1/enrollments` with the view's
  `enroll` object, then `/today`

If generation changes when a learner can start (for example Module 1 ready before the full
outline), extend `view` with a new field and tell onboarding; do not change the meaning of the
existing ones.

**New field for onboarding (generation, 2026-11-20; nothing above changed).** `view.start` =
`{state, concept, minutes, retry}`:

| `state` | Meaning | Suggested `/start` behaviour |
|---|---|---|
| `waiting` | no saved plan yet | keep the skeleton / loading |
| `roadmap_ready` | plan saved; the first lesson is being written | show the plan; Start can wait or show "your first lesson is being written" |
| `first_lesson_ready` | the learner's first lesson is written | enable "Start learning" |
| `first_lesson_failed` | its last job failed, died or was cancelled; `retry: true` | offer a retry (`POST /learning-requests/{id}/regenerate`) |

`concept` is the first activity's concept id (the start level's start concept, else the first in
course order); `minutes` is the request's minutes per day. A course the brain served is
`first_lesson_ready` at once. The web page is not changed yet: that is onboarding's call. Tests:
`services/api/tests/test_start_state.py`.

**`enroll.session_minutes` (generation, 2026-11-20).** For a course generated from a Lesson 0 plan,
the view's `enroll` object also carries `session_minutes` (the learner's true 10/25/60).
`POST /api/v1/enrollments` accepts it, so `/start` posting `published.enroll` unchanged keeps working and
now gets ten-minute days for a ten-minute learner. No web change is needed.

## 4. Live-run findings that belong to generation

From a real Vertex run (Gemini 3.8 Flash) on 2026-11-20, goal "I want to learn SQL for my college
project", door "Filtering a giant music playlist":

1. **The plan is too slow and too big for the moment after Lesson 0.** Outline took 7 min 17 s
   and $1.70 (skeleton, one architect call per module, critic "revise", round 2), producing 8
   modules and 36 lessons. The learner waits on "Writing your course plan" the whole time. The
   onboarding spec asks for a loose roadmap plus a detailed Module 1 only.
2. **Generated courses depend on the old fixed courses.** The architect linked
   `zero:variables-and-types` and `zero:boolean-logic` as prerequisites, so Today opened with
   "Programs and output" from the Zero course. Your partner is already removing these links.
3. **The handoff does reach the plan.** The course was themed on the playlist and planned a
   lesson on the exact gap the snag found ("AND, OR, and Boolean Precedence"). Reading the
   structured profile should make this reliable instead of luck.
4. **Starting point.** Lesson 0 runs no diagnostic, so `enroll.level` is the course's first
   level. Use `calibration` (and later real answers) to choose the start instead.
5. Cost and time per role are in `ai_usage`; per course in `GET /api/v1/admin/engine-costs`.

## 5. Working in parallel

Yes, it can be built in parallel. Rules that keep the two branches from colliding:

| Area | Owner | Notes |
|---|---|---|
| `socrat/onboarding.py`, `tests/test_onboarding.py`, `apps/web/src/app/start/page.tsx` | Onboarding | Generation only calls `profile_for` and `PROFILE_SCHEMA` |
| `socrat/coursegen/*` except `requests.begin`, `catalog/*`, `learn/placement.py`, planner, Today | Generation | |
| `coursegen/requests.py` `begin()` and `view()` | Shared | `begin` is how a claim starts generation: keep its signature `begin(db, settings, user_id, row, parsed)`. `view` fields in 3.3 are read by onboarding |
| `coursegen/intent.py` (`Intent`, `to_brief`, `_soften`) | Shared, generation leads | Onboarding only reads `Intent` and calls `parse`, `apply_adapter`, `from_rules`, `normalise`, `request_key` |
| `coursegen/roles.py` | Shared | Onboarding added the `onboarding` role, its low effort, fast tier and `ROLE_TIMEOUT` |
| `assistant/vertex.py` | Shared | Onboarding added `_thinking()`: low-effort roles think "low" on Vertex unless `SOCRAT_VERTEX_THINKING_LEVEL` is set. This also speeds up generation's low-effort roles (researcher, stylist, experience) |
| Migrations | Coordinate | Onboarding took `0050_onboarding_drafts`. Generation's next one is `0051`; update `schema_revision.py` and the head check in `tests/test_quiz_runtime_tables.py` |
| `config.py` | Shared | Onboarding turned `learning_requests_enabled` on by default and added `onboarding_per_hour` |

Branching: cut generation's branch from `feat/onboarding-lesson0` once it is committed, so the
claim, `begin` and `profile_for` exist. Do not merge `main` into either branch (owner's standing
rule).

## 6. What onboarding will still change (do not build on these)

- The UI, copy and order of `/start`, and the calibration and doors prompts.
- The thresholds behind `pace_level` and `outcome`, and the wording of `verified_baseline`.
- Draft table columns other than `profile` and `request_id`.
- Whether the goal reading stays an in-process background task (it is lost if the API restarts
  mid-read; the rules reading then stands).

Any change to the profile's shape bumps `PROFILE_SCHEMA` and is recorded here.

## 7. Verified and not verified

Verified: `test_onboarding.py` (8 tests, model played by hand); a full Lesson 0 run in Chrome
against Vertex, through sign-in, claim, outline and "Start learning" to Today; full API suite
1139 passed, 21 failed (20 need a local C++/Java toolchain, 1 explainer theme colour; none in
the files above), run before the final Vertex and timeout fixes, which were re-checked with the
onboarding, learning-request and Vertex tests.

Not verified: Lesson 0 with screen readers, on a phone, or in another language; the old
Playwright `learner-journey` suite (it still describes the removed flow); behaviour under several
API processes (the visitor limit and the background reading are per process).

## 8. Running it locally

```bash
# API with Vertex from .env, local SQLite, dev login (from the repo root)
SOCRAT_ENVIRONMENT=development SOCRAT_DATABASE_URL=sqlite:///socrat.live.db \
SOCRAT_DEV_LOGIN_ENABLED=true SOCRAT_PUBLIC_ORIGIN=http://localhost:3000 \
uv run --project services/api alembic upgrade head
# then the same variables with:
uv run --project services/api uvicorn socrat.main:create_app --factory \
  --app-dir services/api/src --host 127.0.0.1 --port 8000 --loop socrat.dev_loop:loop_factory
npm run dev   # web on :3000, open http://localhost:3000/start
```

`.env` points at a placeholder Postgres host and a staging origin, so override them as above.
