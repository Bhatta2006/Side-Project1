# Test status handoff (2026-11-20, evening)

What is tested, what fails right now and why, and what has never been run. Written at `1d4c401` on
`gbuild/feat/course-generator`. Companion to `not-verified.md` (built but not tested end to end) and
`course-generator-backlog.md` (owner decisions at the top: the main path first, the rest halted).

Never commit `apps/web/next-env.d.ts` or `uv.lock`.

## Update 2026-11-21: sections 1-3 and order items 1, 2 (desktop), 3 and 5 done

- **Onboarding 500 fixed.** google-genai 3.x sends through `httpx2`, whose errors do not subclass
  `httpx`'s, so a Vertex timeout escaped `assistant/vertex.py` raw. `_FAILURES` now includes
  `httpx2.TransportError`; `test_vertex.py::test_timeouts_and_transport_errors_become_provider_unreachable`
  covers httpx and httpx2, at the call and mid-stream.
- **Live journey complete for the first time** (run 6, real Vertex, `scripts/dev/journey.mjs`, now in git
  with `scripts/dev/live-journey-api.ps1`): goal -> Lesson 0 -> plan (**T1 176 s**) -> first lesson (**T2 177 s**)
  -> 9-page lesson read -> concept check -> Today, 217 s, no 5xx. The script answers the first option, so the
  check stopped early at 0 of 2 and the plan added a worked example (expected adaptation). Still never reached
  live: a retry at `first_lesson_failed`, the `level_suggestion` offer.
- **Full API suite on `4f51d32` + these fixes: 1219 passed, 25 skipped, 5 failed.** The 5: three in the
  untracked `test_lifecycle.py` (known, predates), and `test_sourced_content` / `test_explainer` whose
  expectations were stale (job order; the light theme now uses the notebook marker) - both fixed, both files
  green. The 20 compiler failures and `test_admin_drafts.py` no longer fail. One explainer test failed once
  while e2e ran in parallel and passed on rerun: possibly timing-sensitive under load.
- **Desktop e2e:** the open items below are fixed (plans dialog dismissed on every first visit, paged
  lessons read to the Recap, new tour order, reworded landing question, weekly assessments are Founding
  Member so the spec grants `plus` via `helpers/learner.ts: grantPlus`, the playground reached from the
  sidebar). Last full desktop run: **27 passed, 1 skipped, 1 failed**; the failure was `visuals.spec.ts`
  timing out on a cold `next dev` compile of `/dev-gallery` (3/3 pass alone; `navigationTimeout` now 60 s).
  The weekly spec found a real bug, fixed: the exam overlay rendered inside the app shell, so the sidebar
  could sit above it and swallow "Save answer"; it is now portalled to `<body>`. The test environment opens
  the weekly exam any day (`SOCRAT_WEEKLY_ANY_DAY=1` in `playwright.config.ts`). **Mobile project still
  never run.**
- **Environment traps:** after a pull that changes `package-lock.json`, run `npm ci` (an old Next refuses to
  start `next dev`); `--basetemp .cache/pt/...` needs `.cache/pt` to exist; a laptop sleeping mid-suite looks
  like a 4-hour hang (check Kernel-Power events 506/507 before debugging).

---

## 1. API test suite (pytest)

Run from the repo root (about 14 minutes):
`uv run --project services/api pytest services/api/tests -q --basetemp .cache/pt/full -p no:cacheprovider`

**Last full run (at `751d201`, after block 4): 1192 passed, 25 skipped, 25 failed.** All 25 predate this work:

| Failing tests | Count | Why | To fix |
|---|---|---|---|
| `test_local_backend.py::test_native_compiled_languages[*-cpp/java]`, `test_compiled_environment_and_oracle_files[cpp/java]` | 18 | no `g++` / `java` on this Windows machine | install the compilers, or run in CI |
| `test_native_limits.py::test_java_uses_problem_budget[*]` | 2 | no `java` | same |
| `test_admin_drafts.py` (3 tests) | 3 | they copy `content/courses`, removed with the built-in courses | rewrite against `content_fixture.py` (`basics`/`algo`) |
| `test_explainer.py::test_artifact_validation_and_compiler_boundaries` | 1 | expects theme token `--primary: #2340E8`; predates | update the expected token or the theme |
| `test_sourced_content.py::test_a_researched_lesson_is_sent_back_until_it_cites_and_then_credits_its_sources` | 1 | predates; not investigated | investigate |

**Commits after that full run** were checked with their related suites only, not the full suite:
`11f441b` (strategist stage; 33 passed), `bc41ba7` (`/start`, web only), `46adb37` (staging compose, docs),
`c04788a` (outcome check; 27 passed), `1d4c401` (replanned lessons, visible wait; 45 passed).
**Next:** one full run on the current head to confirm still 25 failures, none new.

---

## 2. End-to-end browser specs (Playwright)

Run: `PW_CHANNEL=msedge npx playwright test --project=desktop --reporter=line --workers=1`
(Playwright's own Chromium is not installed on this machine; `msedge` uses the installed Edge. Starts the API on
:8000 with a fresh `socrat.e2e.db` and Next on :3000. Ports 8000 and 3000 must be free.)

**What the re-seed changed (uncommitted):** no built-in courses ship, so the e2e server now serves the API tests'
synthetic packs (`basics`, `algo` from `services/api/tests/content_fixture.py`, written to `.cache/e2e-content`).
Specs enrol through the API (`helpers/learner.ts`: `enrolled`, `enrollSignedIn`) instead of the removed course
picker; the quiz answer is always "the right one" (`helpers/answer-keys.ts: RIGHT`); `zero`/`dsa` ids became
`basics` ids (`values`, `text`, `loops`, module `start`, problems `double-it`, `sum-loop`).

**Last complete desktop run (on Next 16.4.6, before the last round of spec fixes): 9 passed, 17 failed,
1 skipped, 2 did not run.** A rerun with the fixes below was stopped at test 9 of 29 to free the ports for the
live browser journey; **it has not been rerun.** The mobile project has never been run.

| Spec / test | Last result | Cause | State |
|---|---|---|---|
| `accessibility.spec.ts` light, dark | failed | two "Log in" buttons (email form + dev form) | **fixed, not rerun** (click scoped to the dev form) |
| `editor.spec.ts` | failed | same | **fixed, not rerun** |
| `learner-journey.spec.ts` (4 tests) | failed | same | **fixed, not rerun**; then the journeys themselves still need a pass |
| `login-design.spec.ts` (2 tests) | failed | same (asserts on the button) | **fixed, not rerun** |
| `landing.spec.ts` hero; "usable without the course API" | failed | the landing page no longer shows course paths (`.path-count`, "Get started with") | **fixed, not rerun** (assertions removed) |
| `tour.spec.ts` | failed | the first-visit plans dialog hides the tour | **fixed, not rerun** ("Maybe later" first) |
| `learning-scope.spec.ts` (4 playground tests) | failed | "Generate" never clickable: most likely the plans dialog | **not fixed**: add "Maybe later" after `page.goto('/playground')` |
| `learning-scope.spec.ts` course search | failed | the search palette lists concepts from `/drills`; "Values" not listed | **not fixed**: check `/drills` for a `basics` learner |
| `keyboard.spec.ts` | failed | "Mark lesson as read" not reached: a paged lesson puts it on the last page (Recap) | **not fixed**: page with Next/Recap first |
| `browser-runner.spec.ts` Python | failed | "Submit solution" not found within 240 s | **not fixed**: investigate (fixture `double-it`, solutions now print `2n`) |
| `today`, `engine`, `visuals` x3, `attribution`, `layout`, others | passed | | |

Earlier runs all failed for environment reasons, now known: (1) Next 16.4.3 stopped `next dev` to show a security
notice (fixed by the upgrade to 16.4.6, `efa8d71`); (2) Playwright's browser was not installed (use `msedge`).

---

## 3. Live browser journey (real Vertex model, real UI)

Script: `.cache/journey/journey.mjs <out-dir> [goal]` (not in git; copy it into `scripts/dev/` to keep it).
Needs the live API on :8000 (Vertex key in `.env`, flags `gen_learner_plan`, `gen_learner_brief`,
`gen_waiting_learner`, `session_one_adaptation`, `SOCRAT_ONBOARDING_PER_HOUR=1000`) and `npm run dev` on :3000.
Drives Edge through `/start` (goal, builder mode, first door, 25 min, win, snag, save as a dev learner) -> plan ->
Start learning -> Today -> the lesson -> its check, with screenshots per step under `.cache/journey/runN/`.

| Run | Result |
|---|---|
| 1 | Lesson 0 -> plan (**T1 97 s**) -> first lesson (**T2 321 s**) -> Today. Stopped: the welcome tour covered "Start lesson" (script fixed: "Skip tour"). **Found two bugs, both fixed in `1d4c401`:** a lesson cancelled because the plan changed stayed cancelled and Today showed "Didn't pass its checks yet"; the `/start` wait showed only grey bars. |
| 2 | Lesson 0 -> plan (**T1 61 s**) -> "Your first lesson is being written" shown, Start hidden (fix confirmed) -> first lesson (**T2 174 s**) -> Today -> lesson "Sorting and Limiting Game Records" (themed on the learner's door, 12 pages). Stopped: "Mark lesson as read" is on the last page (script fixed: pages with Next/Recap). |
| 3 | **Failed at the first screen: `POST /api/v1/onboarding` returned 500.** Not reached the lesson or the check. |

**Bug found in run 3, not fixed yet:** the doors call (`onboarding.start` -> `roles.ask`, 25 s onboarding timeout)
timed out on Vertex's streaming path, which raised a raw `httpx2.ReadTimeout` instead of `ProviderError`;
`doors()` catches only `ProviderError`, so the visitor got a 500 instead of the fallback doors. Seen twice, both the
first onboarding call after a fresh API start (also live run 2's B6). Stored in `error_reports` (fingerprint
`1d760ce8...`). **Fix:** map timeouts and transport errors to `ProviderError("provider_unreachable")` in the Vertex
streaming wrapper (`assistant/vertex.py`), the one place every caller goes through; add a test with a provider
that raises `httpx.ReadTimeout`.

Also in run 3's database: `course generation paused: sql-dc729e reached its budget` (a course of an earlier run hit
its `budget_usd`); expected behaviour, but check that the default course budget fits a whole learner course.

**Never reached in a live browser yet:** marking the lesson read, the concept check, Today after the check, a
retry at `first_lesson_failed`, the `level_suggestion` offer (needs a first-try snag with no gap).

---

## 4. Live model benchmark (API only)

`scripts/dev/bench_claim_to_today.py`; results in `live-run-log.md` (runs 3 and 4). Last (reduced, owner's
choice): exam, sheet music, SQL in builder mode, 25 min: all reached a first lesson (T2 151 / 181 / 308 s).
Not run: sprint and explorer modes, 10-minute sessions for the non-SQL goals.

---

## 5. Order to finish

1. Fix the onboarding timeout 500 (section 3), then rerun the live journey to the end of the check.
2. Fix the four open e2e items (section 2), rerun desktop, then mobile; commit the re-seed.
3. One full API suite run on the head (section 1).
4. Rewrite `test_admin_drafts.py` against the fixture packs (3 of the 25 known failures).
5. Copy `journey.mjs` into `scripts/dev/` so the live journey can be rerun by anyone.
