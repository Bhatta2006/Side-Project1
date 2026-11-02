# API and worker split

Two processes share one database. The **API** serves learners. The **worker** (`python -m socrat.worker`)
runs the outbox, reminder and creator-perk sweeps, Playground explainer jobs and, when enabled, the
course maintainer. Course-generation jobs (outline, lesson packages, exercises, projects) can run in
either process; today's default is the API.

## Why split

Generation is long, CPU and network heavy and bursty. In the API process it competes with learner
requests (one event loop, one GIL) and restarts of the API interrupt it. In the worker it scales and
restarts independently. Jobs are claimed atomically (`coursegen.jobs.claim`: a conditional update on
the job row, safe with any number of processes), and a job whose process died is picked up again
after `STALE_SECONDS`, so moving the runner never loses work.

## Settings

| Setting | Where | Default | Meaning |
|---|---|---|---|
| `SOCRAT_GEN_RUNNER` | API | `true` | Run generation jobs inside the API process |
| `SOCRAT_WORKER_RUNS_GENERATION` | worker | `false` | Run generation jobs in the worker |
| `SOCRAT_WORKER_GENERATION_CONCURRENCY` | worker | `1` (max 16) | Jobs in flight per worker process |
| `SOCRAT_WORKER_HEARTBEAT_FILE` | worker | empty | File the loop touches each iteration; set to `/tmp/worker-heartbeat` in compose |

Both runners on is valid (a job goes to whoever claims it first); neither on means queued jobs wait
forever, which `GET /api/v1/admin/engine-costs` shows as `queue.oldest_queued_seconds` growing.

## Switching, in order

1. Deploy this version with defaults (no behaviour change). Confirm the worker container is healthy
   (`docker compose ps`): the health check runs `python -m socrat.worker --check`, which fails when the
   heartbeat is older than 5 minutes (a hung loop, not only a dead process).
2. Set `SOCRAT_WORKER_RUNS_GENERATION=true` and redeploy only the worker. Both now run jobs.
3. Queue a small generation job, confirm in the admin course builder that it completes, and that
   `queue.queued` drains.
4. Set `SOCRAT_GEN_RUNNER=false` and redeploy the API. Only the worker generates.
5. Rollback is the reverse: `SOCRAT_GEN_RUNNER=true` on the API. Nothing in the database changes.

The worker needs the same AI settings as the API (`SOCRAT_AI_*`, `SOCRAT_GEN_ROLES`, secrets), which
production compose already gives it through `api-environment`; staging's worker has no AI settings, so
do not enable generation there without adding them. The worker needs the execution broker settings
too if exercise or project jobs are used.

## What to watch

- `queue.queued`, `queue.running`, `queue.oldest_queued_seconds` in `GET /api/v1/admin/engine-costs`.
  Alert when the oldest queued job has waited more than about 15 minutes and the course is not paused.
- Worker container health (heartbeat). A failing check restarts the container under
  `restart: unless-stopped` only if the orchestrator acts on health; with plain Compose it is
  visible in `docker compose ps` and in the existing staging alert rules.
- Cost per course in the same report.
