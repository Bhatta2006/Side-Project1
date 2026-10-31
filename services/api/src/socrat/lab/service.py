"""Run lab experiments with the harness and write evidence for the learner's prediction.

The loop is predict, observe, explain. A prediction is committed once, then the true result is
shown (the harness computes it; it is never stored or sent earlier). A prediction within the
experiment's tolerance counts as 1.0, within double the tolerance as 0.5, otherwise 0.0, once
per experiment, with hints recorded as assistance. After the reveal the learner may vary one
parameter to see its effect; those runs are exploration and write nothing.
"""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat import harness
from socrat.catalog.registry import Catalog
from socrat.catalog.schema import Experiment
from socrat.harness import physics
from socrat.learn import service as learn
from socrat.models import Enrollment, Evidence

EXPECTED_SECONDS = 240
NUMBER = re.compile(r"^\s*[-+]?[\d.]+(?:[eE][-+]?\d+)?\s*$")


def public(experiment: Experiment) -> dict:
    """What the learner sees before predicting: the setup, never the result."""
    model = physics.MODELS[experiment.model]
    knobs = {
        k: dict(unit=spec.unit, low=spec.low, high=spec.high, value=experiment.params[k])
        for k, spec in model.params.items()
        if k in experiment.params
    }
    return dict(
        id=experiment.id,
        prompt=experiment.prompt,
        title=model.title,
        model=experiment.model,
        params={
            k: dict(value=v, unit=model.params[k].unit)
            for k, v in experiment.params.items()
            if k in model.params
        },
        predict=dict(name=experiment.predict, unit=model.outputs[experiment.predict]),
        vary=experiment.vary,  # the knob worth trying first
        knobs=knobs,
        hints=experiment.hints,
        difficulty=experiment.difficulty,
    )


def find(catalog: Catalog, concept: str, experiment_id: str) -> Experiment | None:
    if concept not in catalog.concepts:
        return None
    return next((e for e in catalog.concept(concept).experiments if e.id == experiment_id), None)


def problems(experiment: Experiment) -> list[str]:
    """Why an experiment cannot be served (used by the builder's gate)."""
    out = physics.problems(experiment.model, experiment.params)
    model = physics.MODELS.get(experiment.model)
    if model is None:
        return out
    if experiment.predict not in model.outputs:
        out.append(f"cannot predict {experiment.predict!r}; choose one of {sorted(model.outputs)}")
    if experiment.vary and experiment.vary not in model.params:
        out.append(f"cannot vary {experiment.vary!r}; choose one of {sorted(model.params)}")
    return out


def _activity(concept: str, experiment: Experiment) -> str:
    return f"lab:{concept}:{experiment.id}"


def recorded(db: Session, enrollment: Enrollment, concept: str, experiment: Experiment):
    return db.scalar(
        select(Evidence)
        .where(
            Evidence.enrollment_id == enrollment.id,
            Evidence.activity_id == _activity(concept, experiment),
        )
        .order_by(Evidence.created_at.desc())
        .limit(1)
    )


def _simulate(experiment: Experiment, params: dict | None = None):
    return harness.call(
        "physics.simulate", dict(model=experiment.model, params=params or experiment.params)
    )


def _grade(target: dict, text: str, tolerance: float):
    return harness.call(
        "math.check",
        dict(
            op="numeric",
            expected=str(target["value"]),
            given=text,
            unit=target["unit"],
            rel_tol=min(tolerance, 1),
        ),
    )


def predict(
    db: Session,
    enrollment: Enrollment,
    concept: str,
    experiment: Experiment,
    given: str,
    hints_used: int,
    now: int,
) -> dict:
    """Compare a prediction with the simulation. The first one is final and is recorded."""
    truth = _simulate(experiment)
    if not truth.ok:
        return dict(verdict="unavailable", reason=truth.error, evidence=False)
    target = truth.output["outputs"][experiment.predict]
    text = f"{given.strip()} {target['unit']}" if NUMBER.match(given) else given
    graded = _grade(target, text, experiment.tolerance)
    if not graded.ok or graded.output.get("verdict") == "unreadable":
        reason = graded.error or graded.output.get("reason", "")
        return dict(verdict="unreadable", reason=reason, evidence=False)
    verdict = graded.output.get("verdict", "incorrect")
    wrote = False
    if recorded(db, enrollment, concept, experiment) is None:
        near = _grade(target, text, experiment.tolerance * 2)
        close = near.ok and near.output.get("verdict") == "correct"
        score = 1.0 if verdict == "correct" else 0.5 if close else 0.0
        learn.record_evidence(
            db,
            enrollment,
            concept,
            "quiz",
            score,
            _activity(concept, experiment),
            now,
            assistance=min(hints_used, len(experiment.hints)),
            expected_seconds=EXPECTED_SECONDS,
            details={
                "studio": "lab",
                "experiment": experiment.id,
                "predicted": given.strip()[:60],
                "predict": experiment.predict,
            },
        )
        wrote = True
    return dict(
        verdict=verdict,
        evidence=wrote,
        observed=truth.output,
        result=dict(name=experiment.predict, **target),
        explanation=experiment.explanation,
    )


def vary(experiment: Experiment, values: dict[str, float]) -> dict:
    """Re-run with any of the parameters changed. Exploration only: nothing is recorded."""
    merged = {**experiment.params, **values}
    if bad := physics.problems(experiment.model, merged):
        return dict(ok=False, reason="; ".join(bad))
    run = _simulate(experiment, merged)
    if not run.ok:
        return dict(ok=False, reason=run.error)
    return dict(ok=True, observed=run.output)
