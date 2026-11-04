# Production tasks (Master Prompt 2)

Plan: `tasks/production-plan.md`. Finished content-system pilot lives in `tasks/plan.md` and `tasks/todo.md` (untouched).

## Phase 0 re-baseline
- [x] 0.1 Branch confirmed (55 ahead of main); `test_scale.py` + `test_worker_split.py`: 13 passed. ruff clean. **mypy: 10 errors** in `coursegen/{youtube,roles,outline,jobs}.py` from the latest commits (to fix before any push)
- [x] 0.2 (API side) full suite **930 passed, 24 skipped (22m30s)**; ruff clean; mypy now clean (10 errors fixed, types only). Web typecheck and `next build` not run yet
- [x] 0.3 Found and fixed: `scripts/dev/benchmark.py` crashed on the database URL (SecretStr), so it had never run
- [ ] Checkpoint 0: baseline written

## Phase 1 isolation proof
- [x] 1.1 `test_course_isolation.py`: 3 courses generated concurrently with unique markers; every prompt names one course, stored artifacts and learner views carry only their own marker. Passes; a deliberate leak makes it fail. NOT covered: tutor context assembly, review queue across courses
- [x] 1.2 (partial) private course: owner reads, other learner cannot list, join or read it (concept view is scoped by the active enrolment). Other course-scoped reads not yet swept
- [ ] 1.3 Chaos: delete during generation, retry completed job, invalid output, duplicate job, submit during regeneration
- [ ] Checkpoint 1: tests green, any leak fixed at root

## Phase 2 requirements and diversity
- [ ] 2.1 Compare persisted request/brief with Prompt 2 section 3.3 fields
- [x] 2.2 (partial) archetypes now 8. Finding: language and workplace communication have no adapter and run on `general`. Modality and time-budget checks not added yet
- [ ] 2.3 Scenarios A to E as hand-played acceptance tests
- [ ] Checkpoint 2: scorer report for 8 subjects

## Phase 3 live model (needs owner key)
- [x] 3.1 (partial) live benchmark ran for one subject (fractions): 4 of 6 released, 10.0 min, $0.33. Other 7 subjects not run
- [ ] 3.2 targets doc, 3.3 live search check, 3.4 reviewer sample
- [ ] 3.5 Fix planning mismatch (outline plans activities the writer cannot produce); quiz-stage retry

## Phase 4 UI and regression
- [ ] 4.1 Older Playwright suites + visual regression + Lighthouse; 4.2 state/mobile audit of new screens

## Phase 5 security and CI
- [ ] 5.1 Security review; 5.2 draft PR when owner says; 5.3 CI green

## Phase 6 open gaps (flagged off)
- [ ] 6.1 Replan on goal change; 6.2 visual evidence; 6.3 speaking practice (key); 6.4 audio/video upload (decide)

## Phase 7 rollout
- [ ] 7.1 Staging worker split + load test; 7.2 flags in order with rollback; 7.3 pre-merge checks
