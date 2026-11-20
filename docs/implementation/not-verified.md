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
| `/start` page | Does not read `view.start` or `view.level_suggestion` yet (onboarding's page) | onboarding wires them; a browser pass |
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
