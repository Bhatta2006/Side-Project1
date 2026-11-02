"""What each assessment in a lesson measures and how it is scored (master prompt 12.2).

Derived by code from the item's type, not written by a model: an item's format already fixes how
it is evaluated, whether partial credit or alternate answers exist, when feedback is shown,
whether help is allowed and what evidence it contributes. ``describe`` returns one record per
assessment, so the reviewer, the owner and the evaluation harness see the same contract.
"""

from socrat.catalog.schema import Concept

# Quiz item kind -> evidence it gives: picking the answer among options is recognition.
_QUIZ_EVIDENCE = {"mcq": "recognition", "output": "application", "bug": "application"}


def describe(concept: Concept, qualified: str) -> list[dict]:
    out: list[dict] = []
    base = dict(competency=qualified)
    for q in concept.quiz:
        out.append(
            base
            | dict(
                id=q.id,
                format=f"quiz:{q.kind}",
                difficulty=q.difficulty,
                evaluation="hidden answer key, checked on the server",
                scoring="1 if the chosen option is the key, else 0",
                partial_credit=False,
                alternates="none: exactly one option is correct",
                feedback="after the answer: the explanation for every option",
                assistance="none during the answer",
                evidence=_QUIZ_EVIDENCE.get(q.kind, "recognition"),
            )
        )
    for p in concept.prompts:
        points = sum(c.points for c in p.rubric)
        out.append(
            base
            | dict(
                id=p.id,
                format="written explanation",
                difficulty=None,
                evaluation="AI grader against the released rubric; never masters alone",
                scoring=f"rubric, {points} points: "
                + "; ".join(f"{c.criterion} ({c.points})" for c in p.rubric),
                partial_credit=True,
                alternates="any answer meeting the rubric criteria",
                feedback="per criterion, after submission",
                assistance="tutor help is recorded and lowers the weight",
                evidence="explanation",
            )
        )
    for e in concept.exercises:
        out.append(
            base
            | dict(
                id=e.id,
                format=f"exercise:{e.check}",
                difficulty=e.difficulty,
                evaluation={
                    "equivalent": "symbolic equivalence (CAS)",
                    "equation": "same solution set (CAS)",
                    "numeric": "numeric tolerance" + (f", unit {e.unit}" if e.unit else ""),
                    "steps": "each step checked symbolically",
                }[e.check],
                scoring="1 when the check passes, else 0",
                partial_credit=e.check == "steps",
                alternates="any mathematically equivalent answer",
                feedback="hints on request, worked solution after",
                assistance=f"up to {len(e.hints)} hints, recorded",
                evidence="application",
            )
        )
    for x in concept.experiments:
        out.append(
            base
            | dict(
                id=x.id,
                format="predict-observe-explain",
                difficulty=x.difficulty,
                evaluation=f"prediction within {x.tolerance:.0%} of the simulated {x.predict}",
                scoring="prediction checked by the harness; the written why by rubric"
                if x.rubric
                else "prediction checked by the harness",
                partial_credit=bool(x.rubric),
                alternates="any value within the tolerance",
                feedback="the simulation result and the model's explanation",
                assistance=f"up to {len(x.hints)} hints, recorded",
                evidence="transfer" if x.vary else "application",
            )
        )
    for pid in concept.problems:
        out.append(
            base
            | dict(
                id=pid,
                format="judged code",
                difficulty=None,
                evaluation="hidden tests in the sandboxed execution service",
                scoring="accepted when every test passes",
                partial_credit=False,
                alternates="any program that passes the tests",
                feedback="per test after a run; hidden test inputs stay hidden",
                assistance="Socratic hints; a full solution makes a follow-up necessary",
                evidence="application",
            )
        )
    return out
