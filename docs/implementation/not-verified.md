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
| `test_sourced_content.py::test_a_researched_lesson_is_sent_back...` | predates |

## Checked by code only where a person or model judges in practice

- The first-lesson gate cannot check "one example outside the door" (2.5).
- "Ladder ceiling lowered one level" was read as "starts one rung along" (2.4); the owner may have meant the opposite.
- The door does not appear in a shared course's lessons (3.3): a shared lesson is written once for everyone.

## Gamified layer in the paper look (branch gbuild/feat/gamified-ui, 2026-11-21)

The Daybreak look of slices 1 and 2 was replaced the same day by the notebook paper look with CSS frames.

| Area | Not verified | To close it |
|---|---|---|
| Today (game strip, Path tab) | Never seen with a real course: offline onboarding never finishes a course locally; checked on `/dev-mascots/game` with sample data and by typecheck only | open Today for a learner with a generated course |
| Lesson page | Page cards, the ink lesson tube, Soc's bubble on Check pages and the sticky Next bar on phones are typechecked only; never seen on a real lesson | open a lesson at 360px in Classic light, dark and one more palette |
| Quiz and adaptive check | Paper choice tiles, Check stamp, answer sheet, run ribbon and sounds checked on the dev board only (desktop, Classic light and Riso dark), not inside a real quiz | answer a real quiz with `lesson_feel` on, on a phone |
| Session end | Celebration, sticky-note tiles and streak week never rendered from a real `/session-end` reply | finish a session with `session_end` on |
| Sounds and vibration | `playInGame` now plays under the paper look; never listened to on a phone or checked against the silent switch | try on an Android and an iPhone home-screen app |
| Shell | Game-emoji sticker nav icons and the highlighter pill: typechecked only, the app shell needs an enrolled learner | open Today on a phone and on desktop (sidebar open and as an icon rail) |
| Progress header and badges | Seen on the dev board with sample data; never on `/progress` with a real `ProgressView`. Passport is untouched | open Progress for a learner with evidence, with `game_moments` on |
| Game moments (`game_moments`) | Daily goal, level-up, streak ribbon and frozen pebbles seen on the dev board only; once-only memory is per browser | turn the flag on, reach the daily goal and cross a level with a real course |
| Onboarding and landing | `/start` first question and the landing page seen at desktop width in Classic light; the plan-ready celebration needs a real plan | run `/start` to the plan with a live provider |
| Palettes and dark mode | Classic light and Riso dark seen on the dev board; Tide, Lilac, Meadow, Dusk not looked at after the paper change. Dark mode prints filled buttons in dark ink (the light ink failed on the pink marker) | Settings, walk the main pages in each palette, light and dark |
| Contrast | Not measured with a tool: sticky-note tones, the dark-mode stones and the pencil trail | run an axe pass on Today, a quiz and Progress |
| JS budget | Not measured against the 410 KB budget | `npm run build` and the CI budget check |
| Playwright visual specs | Will differ from `gbuild/main` | re-baseline with the e2e re-seed |

## Playground (2026-11-21: fixed, 3D for all, fast declarative sketches, Pro for everyone)

What was broken: a free learner got 402 (`playground=(0, "day")` with billing on); a local API never
ran Playground jobs (only `socrat.worker` claims them; `explainer_runner` now runs them in development);
the web CSP framed visuals only from port 8000 (now `API_INTERNAL_URL`'s origin unless
`NEXT_PUBLIC_EXPLAINER_SANDBOX_ORIGIN` is set); every one-variant declarative sketch failed validation
(no input control: the host page now always has a step slider).

Sketch latency, live, Vertex `gemini-3.8-flash`, 5 prompts run at once (binary search, stack, compound
interest, photosynthesis, SQL LIKE). Before: the default model-written HTML path took 82-175 s per
sketch (median 87 s), 2 of 5 cut off and repaired. The declarative path with default thinking and an
inline AI review took 32-137 s (median 45 s). After (declarative on, `explainer_sketch_effort=low`, the AI
review after delivery, deterministic checks): 13-34 s (median 32 s), 5 of 5 ready, 5 of 5 later
reviews passed (v4 run). Medium effort was slower (19-118 s) and no more accurate.

| Area | Not verified | To close it |
|---|---|---|
| Visual in the app frame | Seen only by opening the frame URL alone: the desktop app's browser pane blocks cross-host subframes (`ERR_BLOCKED_BY_CLIENT`), so the iframe inside `/playground` was not seen rendering | open `/playground` in a normal browser on the pitch setup and generate a sketch |
| Sketch speed | 4 runs of 5 prompts plus 3 in the app; Gemini still sometimes writes broken JSON mid-object at low effort (1-2 repairs in some runs) | more prompts; a JSON schema for Vertex (`response_schema`) if repairs stay common |
| JSON mode on Vertex | Turned off for sketches: with `response_mime_type=application/json` Gemini broke objects mid-way in this test | retest on a newer model |
| Note-number check | Tuned on 10 live sketches; may reject a sketch whose note cites a number that is fine but not drawn (a percentage, a year) | watch `visual attempt ... note says` in the logs |
| 3D for everyone | Tested with the scripted example film only; no live 3D film was generated in this change | one live 3D request as a free learner |
| Pro for everyone (`SOCRAT_EVERYONE_PRO`, on outside tests) | Billing status, paywall welcome and limits checked by tests and the API; not every Pro-gated screen was clicked through | click through assessments and locked topics as a free learner |
| Production runner | `explainer_runner` is off outside development; production still relies on `socrat.worker` | unchanged, but check the worker is deployed with the API |
| Film parse | `film.py` still fails a film the model followed with stray text (the sketch parser now ignores it) | same `raw_decode` fix in `film.parse` |
