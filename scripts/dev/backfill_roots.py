"""Assign a subject root to learner courses made before the course brain (backlog 3.2).

Alias tables only, no model call; such courses become ``serve = "private"`` (never served to
another learner), community courses keep their sharing. Safe to run twice.

  SOCRAT_DATABASE_URL=... uv run --project services/api python scripts/dev/backfill_roots.py
"""

from sqlalchemy.orm import Session

from socrat.config import Settings
from socrat.coursegen.brain.roots import backfill
from socrat.database import make_engine

if __name__ == "__main__":
    with Session(make_engine(Settings().database_url)) as db, db.begin():
        print(f"{backfill(db)} courses given a root")
