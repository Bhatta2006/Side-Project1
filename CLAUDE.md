@AGENTS.md

## What Socrat is, and where it is heading (owner decision, 2026-11-20)

**Target.** Socrat is a personalised course generator and Socratic tutor. A learner says what they
want to learn and tells us about themselves in onboarding (goal, background, pace, preferences); the
engine generates a course, lessons, practice and questions for that one learner. The product is the
verified engine (deterministic checks, graded evidence, adaptive plan), not a fixed syllabus. A model
explains; deterministic code verifies. The learner chooses how strict the tutor, quizzes and
assessments are.

**No built-in courses.** The hand-authored `zero`, `dsa` and `cp` courses are removed, with their
atoms, patterns, quiz families, placement banks, projects and the whole external practice index
(LeetCode, CSES, Codeforces, company bank, sprints, the signed-out "Try it" tutor). Never bring back
a course-id check (`"dsa"`, `"zero"`, `"cp"`), a fixed course sequence, or a reference course or
lesson in an engine prompt. Code practice (editor, judged problems, drills) stays, but only for
generated courses whose shape studio is `code`: it follows the course shape, never its name.

**Where we are.** On branch `gbuild/main` the DSA separation is done and the API suite is mostly
green; the web typechecks and its unit tests pass. API tests that need a catalog use the synthetic
courses `basics` and `algo` in `services/api/tests/content_fixture.py`. Not verified: the Playwright
e2e and visual specs (stale, they still onboard into removed courses), any live model run, and the
onboarding course picker (the cofounder is reshaping onboarding to collect richer learner details).
Known red tests that predate this work: `test_lifecycle.py`, one in `test_explainer.py`, one in
`test_sourced_content.py`. DB tables of removed features were left in place on purpose.

**Next.** (1) Finish the onboarding reshape with the cofounder so every course is generated from the
learner's details. (2) Upgrade the universal engine now that it stands alone. (3) Re-seed the e2e and
visual specs with a generated course. Full detail: `docs/implementation/HANDOFF.md` (update
2026-11-20) and `docs/implementation/universal-engine-plan.md`.
