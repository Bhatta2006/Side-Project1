"""Load test against a running API: concurrent learners reading the app, with p50/p95/p99.

    python scripts/dev/loadtest.py --base http://127.0.0.1:8000 --learners 50 --seconds 20

Needs the API started with ``SOCRAT_DEV_LOGIN_ENABLED=true`` and ``SOCRAT_PUBLIC_ORIGIN`` equal
to ``--origin`` (the default matches the Playwright setup). Each simulated learner signs in once,
then loops over a read mix (today, me, catalogue lists, public engine lists) with a short think
time. Numbers describe the machine and database you ran it on; record them with that context
(see docs/implementation/load-test-results.md) and never present them as production capacity.
It makes no model calls, so it measures serving cost, not generation cost.
"""

import argparse
import asyncio
import json
import statistics
import time

import httpx

MIX = (
    "/api/v1/me",
    "/api/v1/courses",
    "/api/v1/engine/renderers",
    "/api/v1/engine/simulations",
    "/api/v1/locales",
    "/api/health/ready",
)


def pct(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))] if ordered else 0.0


async def learner(client: httpx.AsyncClient, n: int, stop: float, out: dict, think: float):
    login = await client.post(
        "/api/v1/auth/dev-login",
        json={"subject": f"load-{n}", "display_name": f"Load {n}"},
    )
    if login.status_code != 200:
        out["login_failed"] += 1
        return
    i = n
    while time.perf_counter() < stop:
        path = MIX[i % len(MIX)]
        i += 1
        started = time.perf_counter()
        try:
            res = await client.get(path)
            status = res.status_code
        except httpx.HTTPError:
            status = 0
        out["samples"].setdefault(path, []).append((time.perf_counter() - started) * 1000)
        if status != 200:
            out["errors"][f"{path} {status}"] = out["errors"].get(f"{path} {status}", 0) + 1
        await asyncio.sleep(think)


async def main(args) -> dict:
    out: dict = {"samples": {}, "errors": {}, "login_failed": 0}
    limits = httpx.Limits(max_connections=args.learners * 2)
    clients = [
        httpx.AsyncClient(
            base_url=args.base, headers={"Origin": args.origin}, limits=limits, timeout=30
        )
        for _ in range(args.learners)
    ]
    stop = time.perf_counter() + args.seconds
    began = time.perf_counter()
    await asyncio.gather(
        *(learner(c, n, stop, out, args.think) for n, c in enumerate(clients))
    )
    elapsed = time.perf_counter() - began
    await asyncio.gather(*(c.aclose() for c in clients))
    every = [v for vs in out["samples"].values() for v in vs]
    return dict(
        learners=args.learners,
        seconds=round(elapsed, 1),
        think_seconds=args.think,
        requests=len(every),
        requests_per_second=round(len(every) / elapsed, 1),
        p50_ms=round(statistics.median(every), 1) if every else None,
        p95_ms=round(pct(every, 0.95), 1),
        p99_ms=round(pct(every, 0.99), 1),
        errors=out["errors"],
        login_failed=out["login_failed"],
        by_route={
            p: dict(n=len(v), p50_ms=round(statistics.median(v), 1), p95_ms=round(pct(v, 0.95), 1))
            for p, v in sorted(out["samples"].items())
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--origin", default="http://localhost:3000")
    parser.add_argument("--learners", type=int, default=25)
    parser.add_argument("--seconds", type=float, default=15)
    parser.add_argument("--think", type=float, default=0.2, help="seconds between a learner's requests")
    print(json.dumps(asyncio.run(main(parser.parse_args())), indent=2))
