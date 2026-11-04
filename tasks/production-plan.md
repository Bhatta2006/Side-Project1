# SOCRAT production plan (against Master Prompt 2)

## Context
Master Prompt 2 asks for an audited, repaired, integrated course-generation and learning engine. Reading
`docs/implementation/HANDOFF.md`, `ule-gap-audit.md` and the progress log shows most of it is already
built on `feat/universal-engine` (55 commits ahead of `main`, pushed, no PR, 798 API tests green at last
full run, all new features behind flags that default off). So "production" here is not more features. It is
**proving what exists, closing the few real gaps, and rolling it out safely**. Re-building the engine
would break the owner's rules (no rewrites, additive migrations, flags off, no merging main into the branch).

Honest status: nothing has run against a live model (only hand-written replies and a stand-in model through a
relay), CI and the older Playwright/visual suites have never run on this branch, and I found no dedicated
concurrent multi-course isolation test (Prompt 2 section 19.3). I have not re-run any tests in this planning
pass; the numbers above are from the repo's own docs.

## Prompt 2 section vs. what exists (from the docs, not re-verified)
| Prompt 2 | State | Production action |
|---|---|---|
| 2 Audit | Done in `universal-engine-plan.md` and `ule-gap-audit.md` | Refresh once after live run |
| 3 Understanding, requirements object | Intent parser, `learning_requests`, brief | Check object has every field in 3.3 (version, timestamp, owner) |
| 4 Course isolation | Owner checks, per-course scoping | **Prove** with concurrent test + marker injection (new) |
| 5, 6 Blueprint, pedagogy | Competency graph, strategist, time-aware outlines | Verify on 8 subjects (new) |
| 7 to 10 Lessons, resources, assessment, practice | Built, search is flagged and never run live | Live-model pass |
| 11 Validated UI registry | Renderer registry, host, fallbacks | Run browser suites |
| 12, 13 Adaptation, tutor | Built | Per-course tutor context check inside isolation test |
| 14, 15 Pipeline, state | Retry, dead-letter, progressive start, revisions | Chaos cases from 19.5 (new) |
| 16, 17 UX, security | Partial, older suites unrun | a11y/layout/visual suites, security review |
| 18 Cost and latency | Reports exist | Set targets from live-run numbers |
| 19 Tests | Strong unit/e2e, gaps above | New tests below |
| Scenarios A to E | Partly (no audio/video upload; speaking recording needs a speech key) | Acceptance run per scenario |

## Phases (vertical, each leaves the branch green)

### Phase 0: Re-baseline (no code)
- From `D:\Socrat`: `git fetch`, confirm branch state, run `test_scale.py` + `test_worker_split.py` with a `--basetemp` I own.
- Run the full API suite once (about 21 min) to replace the stale 798 number; ruff, mypy, web typecheck, `next build`.
- Exit: written baseline in the progress log.

### Phase 1: Isolation proof (Prompt 4, 19.3) , highest value, needs no key
- New `services/api/tests/test_course_isolation.py`, using the `Scripted` pattern from `test_coursegen.py` and `test_engine_e2e.py`:
  three unrelated courses (DSA, guitar, quantum) under one learner, generated concurrently, unique marker strings injected into each course's sources, lessons, quiz, tutor context, resources and evidence.
- Assert no marker appears in another course's prompt, retrieval, tutor context, review queue or API payload; repeat with two users (403/404 on cross-user reads).
- Add chaos cases (19.5): delete during generation, retry a completed job, invalid model output, duplicate job, assessment submit during regeneration.
- Exit: tests pass; any leak found is fixed at the root and logged.

### Phase 2: Requirements and subject-diversity (Prompt 3, 6, 19.4)
- Check the persisted request/brief against 3.3 fields; add only missing optional fields, additive migration with downgrade test if needed.
- Extend `engine/benchmark.py` archetypes from 5 to the 8 in 19.4 (add language learning, visual/creative, professional communication; keep programming, maths, science, music, university subject). Deterministic scorer checks modality fit (no MCQ-only for code or music), time-budget realism (5 min vs 60 min), prerequisite order.
- Encode Scenarios A to E as acceptance tests where the engine can run them hand-played.
- Exit: scorer report for all 8 with failures listed, not hidden.

### Phase 3: Live-model pass (needs the owner's key; not ChatGPT 5.5)
- Run `scripts/dev/benchmark.py` for the 8 requests with per-role models set via `SOCRAT_GEN_ROLES`.
- Record JSON conformance, cost per course, latency per role, time to first lesson; then fix prompts, not the validators.
- Turn those numbers into the Prompt 18.3 targets in a doc (measured, not invented).
- Run the grounded-search path live once (`research_providers`) and verify citations.
- Exit: live run log + targets; qualified reviewers sample the output (facts, prerequisites, teaching quality).

### Phase 4: UI, accessibility, regression (Prompt 11, 16, 17)
- Run the Playwright suites never run on this branch (`learner-journey`, `layout`, `accessibility`, `landing`, `keyboard`), the visual-regression config, Lighthouse budgets (250 KB first-load).
- Check loading/empty/failed/partial states and reduced-motion/mobile for new screens (`/new`, Reviews, Tasks, visuals).
- UI polish follows the `unslop` skill and the notebook design system; show an audit before touching any page.
- Exit: suites green or each failure triaged (branch regression vs. pre-existing).

### Phase 5: Security and CI (Prompt 17)
- Security review of: sandboxed code execution limits, prompt-injection handling of retrieved text, rate limits, hidden test cases never reaching the client, CSRF on new routes.
- Open a **draft** PR (only when told) so CI runs; fix what it finds.
- Exit: CI green on the branch.

### Phase 6: Real gaps still open
Small slices, each flagged off, tests first:
1. Replan future modules when the learner changes their goal (named "not done" in the log).
2. Visuals recording evidence (events like `predicted`, `marker_placed`).
3. Speaking/recording practice for Scenario D: needs a speech key (Sarvam or other) , **ask the owner**; until then labelled self-assessed.
4. Audio/video upload for tasks (currently a link) , decide with the owner whether it is worth it.

### Phase 7: Rollout
- Follow `docs/operations/api-worker-split.md` on staging (add AI settings to the staging worker first), staging load test on Postgres, shared rate limits if Redis is provisioned.
- Flags in order, each with a rollback: `learning_requests_enabled`, `gen_visuals`, `maintainer_enabled`, `lite_mode_enabled`, `explainer_sketch_declarative`, `research_providers`.
- Before merge: renumber migrations only if `main` gained any; never merge `main` into the branch.

## Skills and plugins used / to use
- Used: `planning-and-task-breakdown`. At execution: `test-driven-development` (isolation + chaos tests), `debugging-and-error-recovery` (any leak or flake), `security-and-hardening` (Phase 5), `browser-testing-with-devtools` + `frontend-ui-engineering` + `unslop` (Phase 4), `code-review-and-quality` before each push, `git-workflow-and-versioning` for commits, `ci-cd-and-automation` and `shipping-and-launch` (Phases 5 and 7), `find-docs`/`ctx7` for Next.js 16 docs, `doubt-driven-development` on the isolation design.
- Plugins: the catalog search found nothing that fits this repo. "Wave Planning" (parallel worktree execution) and "learning-planner" are the nearest, but neither is needed; I'm not suggesting an install.
- Sarvam MCP tools are available for Indic speech/translation checks in Phase 6; the product code still needs its own key.

## Bookkeeping
`tasks/plan.md` and `tasks/todo.md` already exist for the finished content-system pilot (all items checked). I will not overwrite them. On approval I'll write this plan to `tasks/production-plan.md` and `tasks/production-todo.md` and add a line to the progress log in `universal-engine-plan.md`.

## Verification (end to end)
Full API suite + ruff + mypy; web typecheck, build, all Playwright suites; isolation tests; benchmark scorer for 8 subjects; live benchmark with cost/latency table; CI green on the draft PR; staging smoke including worker heartbeat.

## Decisions needed from the owner
1. Model key for Phase 3 (and a speech key for Phase 6.3).
2. Who the qualified reviewers are for the evidence library and the benchmark sample.
3. Whether to open the draft PR now (Phase 5) or after Phase 4.
