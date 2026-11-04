"""At most one open generation job per course, kind and target. Additive.

Callers checked ``jobs.active()`` and then inserted, so two concurrent requests (a double-click
on "regenerate", two workers releasing the same concept) could both queue the same lesson and
pay for it twice. A partial unique index makes the database refuse the second one;
``jobs.enqueue`` turns that into ``AlreadyQueued``.

Existing duplicates (if any) would block the index, so all but the oldest open job of each
group are marked ``cancelled`` first, with a log entry. No row is deleted. The downgrade drops
the index only; cancelled duplicates stay cancelled.
"""

import json
import time

import sqlalchemy as sa
from alembic import op

revision = "0045_one_open_generation_job"
down_revision = "0044_course_revisions"
branch_labels = None
depends_on = None

OPEN = "state IN ('queued', 'running')"


def upgrade():
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            f"SELECT id, course_id, kind, target, log FROM generation_jobs WHERE {OPEN} "
            "ORDER BY created_at, id"
        )
    ).fetchall()
    seen: set[tuple[str, str, str]] = set()
    stamp = int(time.time())
    for job_id, course_id, kind, target, log in rows:
        key = (course_id, kind, target or "")
        if key not in seen:
            seen.add(key)
            continue
        entries = json.loads(log) if isinstance(log, str) else list(log or [])
        entries.append({"role": "system", "event": "cancelled_duplicate", "at": stamp})
        bind.execute(
            sa.text(
                "UPDATE generation_jobs SET state = 'cancelled', log = :log, updated_at = :at "
                "WHERE id = :id"
            ),
            {"log": json.dumps(entries), "at": stamp, "id": job_id},
        )
    op.create_index(
        "uq_generation_jobs_one_open",
        "generation_jobs",
        ["course_id", "kind", "target"],
        unique=True,
        sqlite_where=sa.text(OPEN),
        postgresql_where=sa.text(OPEN),
    )


def downgrade():
    op.drop_index("uq_generation_jobs_one_open", table_name="generation_jobs")
