# Not verified: what is built but not tested end to end

Kept current with every change to the course generator (started 2026-11-20). One line per gap: what is missing,
and what would close it. "Scripted" means tested with a model that replies from a script, not a real provider.
Remove a line only when the check it names has run.

## Live model (Vertex `gemini-3.8-flash`)

| Area | Not verified | To close it |
|---|---|---|
| Benchmark (2.5) | Only 6 SQL runs; the exam and non-programming goals never ran (rate limit, then stopped at $4.72) | rerun `scripts/dev/bench_claim_to_today.py` with `SOCRAT_ONBOARDING_PER_HOUR=1000` (~$12) |
| Benchmark (2.5) | The three fixes it led to (gate waived on the last round, ```` ```sql ```` allowed, all-caps keywords) were made after the API started | one more benchmark run |
| Course brain (1.2) | A second learner served a *published* shared course with zero model calls | two accounts, the first publishes, the second asks the same, with `course_brain` on |
| Scoper (3.5) | Never called a real model | one research job with `brain_scoper` on |
| Outcome / gap map (2.1) | Seen live only with the old keyword check (every outcome was rejected) | the benchmark rerun above |
| Session one (2.4), served overlay (3.3) | No real learner session; scripted evidence only | a live learner doing session one, on a built and on a served course |
| Refresh sweep (3.6) | Not run in a real worker loop | start the worker with `SOCRAT_BRAIN_REFRESH_SWEEP_SECONDS` set and an old unit |

| Review variants (4.2), module exams (4.1), outline tags (4.3) | Scripted only: no live model has written variants or an exam | one live course with `gen_review_variants`, `gen_module_exams`, `gen_outline_tags` on |
| Module exams (4.1) | A learner taking a checkpoint that mixes exam items (only the pool is checked) | a checkpoint session in a test or a live run |

## Real infrastructure

| Area | Not verified | To close it |
|---|---|---|
| Waiting learner (PR 5) | The 2-minute re-claim against a real worker kill | kill a worker mid-outline, watch a second one take the job |
| Waiting learner (backlog 7) | Calls in a job a learner waits on are now cut at `gen_waiting_timeout_seconds` (120 s) and the job retries; tested on the settings only, not against a slow real provider | a live job with a provider that stalls |
| Brain concurrency (3.4) | 8 concurrent first requests on one database (one root, one course, one research job) | a threaded test on Postgres |
| Brain benchmark (3.4) | `bench_brain.py` (cold / from material / direct reuse) not written | write it; needs a live model |
| Deployed config (1.3) | That the deployed environment does not set `SOCRAT_GEN_RELAXED_GATES` | check the deployment's variables |

## Web

| Area | Not verified | To close it |
|---|---|---|
| Admin "Course brain" tab (3.7) | Typechecked only; never opened in a browser | open `/admin` -> Course brain as an admin |
| `/start` page | Wired to `view.start` and `level_suggestion` (2026-11-20); typechecked, never driven in a browser (Lesson 0 needs a model, the e2e server has none) | a browser pass against a live or scripted model |
| Staging | The four main-path flags are on in the compose file; no AI provider or key is configured there | add `SOCRAT_AI_PROVIDER` and its key as staging secrets, then one learner through `/start` |
| E2E and visual specs | Still onboard into removed courses; red | re-seed with a generated course (backlog 5) |

## Known red tests (not caused by this work)

| Test | Why |
|---|---|
| `test_admin_drafts.py` x3 | copy `content/courses`, removed with the built-in courses |
| `test_local_backend.py`, `test_native_limits.py` (20) | no `g++` / `java` on this machine |
| `test_explainer.py::test_artifact_validation_and_compiler_boundaries` | theme token (predates) |
| `test_sourced_content.py::test_a_researched_lesson_is_sent_back...` | predates |

## Checked by code only where a person or model judges in practice

- The first-lesson gate cannot check "one example outside the door" (2.5).
- "Ladder ceiling lowered one level" was read as "starts one rung along" (2.4); the owner may have meant the opposite.
- The door does not appear in a shared course's lessons (3.3): a shared lesson is written once for everyone.

## Playful look: Daybreak (branch gbuild/feat/gamified-ui, 2026-11-21)

| Area | Not verified | To close it |
|---|---|---|
| Today (game strip, Path tab) | Never seen with a real course: offline onboarding never finishes a course locally; checked on `/dev-mascots/daybreak` with sample data and by typecheck only | open Today for a learner with a generated course |
| Quiz and adaptive check | Feedback sheet, flame combo and sounds checked on the dev page only, not inside a real quiz | answer a real quiz with `lesson_feel` on |
| Session end | Celebration, stat tiles and streak week never rendered from a real `/session-end` reply | finish a session with `session_end` on |
| Sounds and vibration | Played without errors; never listened to on a phone or checked against the device's silent switch | try on an Android and an iPhone home-screen app |
| Notebook look | The six notebook palettes were not re-checked after the ink change (frames skip only under Daybreak). Slice 2: on the dev board under Classic every `.db-only` part is hidden and choice tiles keep their notebook corners; real pages not walked | switch to Classic in Settings and walk Today, a lesson, Settings |
| Dark mode, Daybreak | Slice 2 looked at the dev board in dark (profile header, tiles, badges): fine. Real pages not walked. The filled primary now keeps its light value in dark mode (white on the brighter `-hi` failed AA) | Settings, Dark, walk the main pages |
| Lesson page (slice 2) | Page cards, the green lesson bar, Soc's bubble on Check pages, the sticky bottom Next bar on phones and the dark code blocks are typechecked only; never seen on a real lesson (needs a generated course) | open a lesson at 360px in Daybreak light, dark and Classic |
| Quiz page (slice 2) | Choice tiles, tap clack, marigold run bar and the sticky Check bar checked on the dev board at 375px only | answer a real quiz with `lesson_feel` on, on a phone |
| Shell (slice 2) | Game-emoji nav icons and the tinted active pill: typechecked only, the app shell needs an enrolled learner | open Today on a phone and on desktop (sidebar open and as an icon rail) |
| Progress header and badge stickers (slice 2) | Seen on the dev board with sample data; never on `/progress` with a real `ProgressView`. Passport is untouched | open Progress for a learner with evidence, with `game_moments` on for the stickers |
| Game moments (`game_moments`, slice 2) | Daily goal reached, level-up, streak milestone ribbon and frozen pebbles seen on the dev board only; once-only memory is in localStorage, per browser | turn the flag on, reach the daily goal and cross a level with a real course |
| Onboarding and login visuals (slice 2) | Pebble trio, goal names on the time choices and login headline seen at 375px; the plan-ready celebration needs a real generated plan | run `/start` to the plan with a live provider |
| Contrast (slice 2) | Computed, not measured in a browser tool: white on every palette primary now ≥ 4.6:1 (Ruby, Lagoon, Sunset darkened), correct and wrong Check buttons deepened to ≥ 4.5:1, ribbon text 5.1:1. Text on the game colours themselves (white on `--db-correct`) is still 2.9:1 wherever slice 1 used it | run an axe pass on Today, a quiz and Progress |
| JS budget (slice 2) | New components (game moments, profile header, nine emoji) not measured against the 410 KB budget | `npm run build` and the CI budget check |
| Playwright visual specs | Will differ: the default look changed | re-baseline with the e2e re-seed |
