# Load test results

Tool: `scripts/dev/loadtest.py`. Each simulated learner signs in with dev login, then loops over
six read routes (`/me`, `/courses`, `/engine/renderers`, `/engine/simulations`, `/locales`,
`/api/health/ready`) with a 0.2 s think time. No model calls, so this measures **serving**, not
generation cost.

## Run of 2026-11-02 (slice 9)

Setup, stated because numbers mean nothing without it: one Windows 11 laptop, one `uvicorn`
process, SQLite, the load generator on the same machine, content catalog prewarmed
(`SOCRAT_PREWARM_CONTENT=true`), offline AI provider, three hand-authored courses and no
generated ones.

| Learners | Requests | Req/s | p50 | p95 | p99 | Errors |
|---|---|---|---|---|---|---|
| 25 | 1,994 in 20 s | 98.6 | 41.7 ms | 84.6 ms | 143.7 ms | 0 |
| 100 | 5,507 in 20 s | 270.8 | 160.9 ms | 294.6 ms | 351.2 ms | 0 |

Per route at 100 learners, p95: `/me` 299 ms, `/courses` 313 ms, `/engine/renderers` 292 ms,
`/engine/simulations` 275 ms, `/locales` 284 ms, `/health/ready` 296 ms. Routes are within noise of
each other, so the limit here is the single process and the shared machine, not one slow route.

## What the first run found (fixed)

Before the fix, 25 learners hitting a **cold** server all timed out on `/api/v1/courses`
(30 s, error rate 100 % for that route). `default_catalog()` was cached with `functools.cache`,
which lets every concurrent caller compute on a miss, so each of 25 requests parsed the whole
catalog (about 6 s of CPU apiece). Fixes: `catalog.registry.single_flight` (the first caller
loads, others wait) and a catalog load at API start (awaited when `prewarm_content` is on,
in a background thread otherwise). Regression test:
`test_cold_catalog_is_loaded_once_when_many_requests_arrive_together`.
Without prewarm, the first request after a restart still waits about 6 to 8 s (p99 7.7 s in that
run); set `SOCRAT_PREWARM_CONTENT=true` in production so readiness only reports once loaded.

## What this does not tell you

- Production capacity. Postgres, several processes, a network and real content volume are all
  missing. Re-run against the staging stack before quoting a number to anyone.
- Write paths (enrolment, quiz answers, code submission) and the tutor are not in the mix.
- Cost: see `GET /api/v1/admin/engine-costs` for generation spend per course and per role.
- Re-run command: `python scripts/dev/loadtest.py --base http://127.0.0.1:8000 --learners 100 --seconds 20`
  against an API started with `SOCRAT_DEV_LOGIN_ENABLED=true` and `SOCRAT_PUBLIC_ORIGIN=http://localhost:3000`.
