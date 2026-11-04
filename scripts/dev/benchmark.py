"""Run the course-generation benchmark against a live model (master prompt 16.1).

For each archetype request in ``socrat.engine.benchmark.REQUESTS``: parse the intent, write the
outline (architect and critic), publish it, write the first slice of lessons, then score the
course with ``benchmark.score`` and print a JSON report. Uses the model settings in the
environment (``SOCRAT_AI_*``, ``SOCRAT_GEN_ROLES``); it spends real money, capped by each brief's
budget. Run against a throwaway database:

    SOCRAT_DATABASE_URL=sqlite:///bench.db SOCRAT_AI_PROVIDER=anthropic ... \
    uv run --project services/api python scripts/dev/benchmark.py [--only music] [--dry-run]

``--dry-run`` lists the requests without calling a model. The report is triage, not a verdict:
qualified people must review a sample (``benchmark.HUMAN_REVIEW``).
"""

import argparse
import asyncio
import json
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.config import Settings
from socrat.coursegen import intent as intents
from socrat.coursegen import jobs, prefetch
from socrat.database import make_engine
from socrat.engine import benchmark
from socrat.models import Base, GenerationJob


async def run(only: str | None, dry: bool, roles: dict | None = None) -> list[dict]:
    chosen = [r for r in benchmark.REQUESTS if only in (None, r[0])]
    if dry:
        return [dict(id=i, request=text, adapter=a) for i, text, a in chosen]
    settings = Settings()
    if roles is not None:  # replaces SOCRAT_GEN_ROLES from the environment for this run
        settings = settings.model_copy(update={"gen_roles": roles})
    engine = make_engine(settings.database_url_value)
    Base.metadata.create_all(engine)
    base = default_catalog()
    reports = []
    for case, text, expected in chosen:
        parsed, source = await intents.parse(engine, settings, text)
        parsed = intents.apply_adapter(parsed, text)  # as the learner request route does
        course_id = intents.slug(parsed.subject, "bench", case)
        brief = intents.to_brief(parsed, course_id, 5.0)
        with Session(engine) as db, db.begin():
            jobs.enqueue(db, "outline", course_id, {"brief": brief.model_dump(mode="json")}, None)
        while await jobs.run_once(engine, settings, base):
            pass
        with Session(engine) as db, db.begin():
            if generated.course(db, course_id) is None:
                reports.append(dict(case=case, error="no outline"))
                continue
            generated.publish(db, base, course_id)
            prefetch.initial(db, course_id)
        while await jobs.run_once(engine, settings, base):
            pass
        with Session(engine) as db:
            course = generated.course(db, course_id)
            ran = list(
                db.scalars(select(GenerationJob).where(GenerationJob.course_id == course_id))
            )
            result = benchmark.score(course, generated.merged(base), parsed.adapter, ran)
        reports.append(dict(case=case, intent_source=source, expected_adapter=expected, **result))
    return reports


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--gen-roles", help="JSON replacing SOCRAT_GEN_ROLES for this run")
    args = parser.parse_args()
    print(
        json.dumps(
            asyncio.run(
                run(args.only, args.dry_run, json.loads(args.gen_roles) if args.gen_roles else None)
            ),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
