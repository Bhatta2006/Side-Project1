# Harness and math workbench

**Principle:** the engine is the product; the model is a replaceable part (like Claude Code's harness).
Models explain and ask. Deterministic, sandboxed capabilities decide what is true.

## Harness (`services/api/src/socrat/harness/`)
- `registry.py`: `Capability(name, summary, input model, run, parameters, timeout)`, `call(name, args) -> Result`.
  `call` never raises; bad input and timeouts come back as `Result(ok=False, error=...)`.
- `sandbox.py`: one persistent worker process (spawn); killed and restarted when a call exceeds its time limit.
- `library.py`: built-in capabilities. Today: `math.check` (equivalent, equation, steps, numeric with units).
- Callers: tutor tools (`assistant/tools.py`, admins only), builder gates (`coursegen/package.py`), studios (`workbench/`).
- Add a subject by registering a capability; nothing else changes.

## Math workbench
- Builder: shapes with the `cas` tool ask the quiz role for 3-6 `exercises`; `check_exercises` rejects any whose
  reference answer the harness does not accept, or whose plot expressions do not parse. Failures go back to the author.
- Learner API (admin-only while testing): `GET /api/v1/workbench/{course}/{concept}` (no answers),
  `POST /api/v1/workbench/check` (grades with the harness). Correct answers write `quiz` evidence once, with hints as
  assistance; "show me" writes a miss; wrong tries are feedback only.
- UI: `components/studio/workbench.tsx` with JSXGraph graphs (`graph.tsx`), registered in the studio registry.

## Physics lab (predict, observe, explain)
- Capability `physics.simulate` (`harness/physics.py`): vetted closed-form models (projectile, free_fall, pendulum,
  spring_mass, circuit) with parameter limits and units. Each has a test against a known result.
- Builder: shapes with the `simulation` tool ask for 2-4 `experiments` (model, params, quantity to predict, optional
  parameter to vary). `check_experiments` rejects ones the simulation cannot run, or whose prompt states the answer.
  The true result is never stored: the harness computes it when the learner predicts.
- Learner API (admin-only while testing): `GET /api/v1/lab/{course}/{concept}` (setup, no results),
  `POST /api/v1/lab/predict` (grades with `math.check` numeric and the experiment's tolerance, reveals the run),
  `POST /api/v1/lab/vary` (explore one parameter after predicting; writes nothing).
- Evidence: the first prediction per experiment is recorded once as `quiz` evidence: 1.0 within tolerance, 0.5 within
  double, else 0.0; hints count as assistance.
- UI: `components/studio/lab.tsx` (SVG trace, readout, slider), registered as the `lab` studio.
- Not graded: the "explain" step is shown (model-written why) but there is no free-text grading yet.

## Not yet
- Existing code execution (`coursegen/execute.py`) is not a harness capability yet.
- Tutor-side evidence from `math_check` is advisory; only workbench grading writes evidence.
- Graded free-text explanations for the lab; more experiment models (waves, optics, thermal).
