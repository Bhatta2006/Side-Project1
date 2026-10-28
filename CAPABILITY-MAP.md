# Capability Map: Adaptive mentor and course studios

Draft for review. Direction and decisions: `docs/ideas/adaptive-mentor-course-studios.md`.
Everything is admin-only while testing.

| Module id | Responsibility | Depends on |
|---|---|---|
| course-shape | `CourseShape` (studio, practice loop, evidence kinds) on a course; architect proposes it, critic checks it | — |
| answer-checking | Shared checkers run in the browser (Pyodide): symbolic equivalence (SymPy), numeric with units, step checks | — |
| sourced-content | Researcher agent: open and public sources only, license allow-list, citations and provenance on every lesson, cache and reuse to keep cost low | course-shape |
| studio-shell | Fixed spine plus a dynamic Studio slot; renderer registry per studio type; Evidence adapts to evidence kinds; existing code practice becomes the "code" studio | course-shape |
| mentor-core | Teaching-moves policy over the existing skill profile and planner; bounded autonomy (auto vs propose); undo; learner-visible "why" log | course-shape |
| harness | The engine's single contract: typed, sandboxed, verified capabilities (math.check first) called by the tutor, builder gates and studios; the model is replaceable | answer-checking |
| math-workbench | Studio for math: JSXGraph graphs, answer and derivation checking | studio-shell, answer-checking, sourced-content |
| physics-lab | Studio for physics: simulations (PhET for testing, own JSXGraph sims), predict-observe-explain loop, units checking | studio-shell, answer-checking, math-workbench, sourced-content |

Build order:

1. course-shape, answer-checking (independent)
2. studio-shell, sourced-content, mentor-core (each needs only course-shape)
3. math-workbench
4. physics-lab

Boundaries between modules:

- `course-shape` owns the schema; everyone else reads it.
- `mentor-core` never renders UI; it writes decisions and the "why" log. `studio-shell`
  shows them.
- `harness` is the product: subject abilities (math, units, simulations, CAD, music) are registered
  capabilities, never special cases inside a studio or a prompt. Models explain; capabilities verify.
- `answer-checking` has no knowledge of courses; studios call it.
- `sourced-content` owns the license allow-list and the citation record; builders may not
  bypass it.
