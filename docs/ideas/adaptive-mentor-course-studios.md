# Adaptive mentor and course studios

Status: direction agreed 2026-10-28. Admin-only while testing. No code yet.

## Problem statement

How might we make the app's sections, practice and evidence come from what a course needs,
and put a mentor behind them that decides what each learner should learn next, how to teach
it, and with which tool, for any subject?

## Recommended direction

1. **A `CourseShape` on every course**, chosen by the architect agent and checked by the
   critic: the studio type (code, workbench, lab, later score, viewport, timeline), the
   practice loop (solve, derive, predict-observe-explain, perform and compare, build to spec,
   make and critique), and the evidence kinds (tests pass, derivation checks, numeric answer
   with units, recording analysis, geometry check, rubric critique).
2. **A fixed spine plus a dynamic studio.** Today, Path, Evidence and Settings stay on every
   course. Practice and Playground become one Studio slot whose name, route and tools come
   from the course's shape. Evidence shows the kinds that apply.
3. **Mentor v0 with bounded autonomy.** A decision step over teaching moves (explain, worked
   example, retrieval, interleave, challenge, reflect, project, break) built on the existing
   skill profile, planner and proposals.
   - Acts on its own, reversibly: reorder the next few items, insert a refresher or
     retrieval, adjust difficulty and pacing, switch explanation style.
   - Proposes, learner decides: dropping topics, changing goal or depth, changing studio.
   - Rules decide what to do; the model only explains and writes.
   - Every action is written to a **learner-visible "why" log**.
4. **Pilot: physics and math, admin only.** Success is the owner taking three courses
   end-to-end and judging the sections, teaching and adaptation.

## Decisions (owner, 2026-10-28)

- Pyodide, SymPy and JSXGraph are cleared for commercial use.
- PhET may be used for testing now. Note: PhET's help center says commercial use of its
  simulations needs a separate license, so this stays admin-test-only until that is settled.
- The AI budget for the mentor and the builders is kept small without lowering quality:
  rules first, cached and reused results, models only where language is needed.
- Course-building agents must use open-source and publicly available resources and cite them
  (provenance), never copy, so copyright is respected.
- The mentor's "why" log is visible to the learner.

## Evidence base (checked 2026-10-28)

- A purpose-built AI tutor beat an active-learning class in a Harvard physics trial
  (Kestin et al., Scientific Reports 2025); one course, two lessons, so promising not settled.
- Gains came from built-in pedagogy, not a powerful model. Tutor CoPilot raised mastery by
  prompting students to explain their thinking.
- Shallow Bayesian knowledge tracing matches deep neural tracing and is easier to explain.
  FSRS is the modern open scheduler for retention.
- No direct evidence that adapting to interest improves outcomes: treat it as a hypothesis.
- Vision models alone hallucinate on student diagrams; verify with code first.
- License traps: OpenStax books are mostly CC BY-NC-SA; GeoGebra needs a commercial license;
  replicad appears to be AGPL (unverified).

## Key assumptions to validate

- [ ] The architect picks a sensible shape for 10 varied subjects (human check).
- [ ] Learners accept automatic adjustments (watch the undo rate).
- [ ] Generated physics simulations are correct (check against known results).
- [ ] Interest-based adaptation helps (not promised until measured).

## Not doing

- Music, CAD and animation studios (the shape schema leaves room; nothing built).
- Fully AI-generated UI per course.
- Deep-learning knowledge tracing.
- Copying non-commercial or unlicensed content.
- Using a vision model as the only grader of creative work.

## Open questions

- Cost per learner of the mentor loop under the existing AI budgets (measure in the pilot).
- When PhET's commercial terms are settled for a public launch.
