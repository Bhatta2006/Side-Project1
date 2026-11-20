"""Claim -> Today benchmark (course-generator-backlog.md 2.5): Lesson 0 through a real API and model.

For each goal x mode x minutes it signs in a fresh dev account, runs Lesson 0 (doors, the mode and
the first door, the win and the snag answered option by option), claims, and polls ``view.start``:

  T1  claim -> roadmap_ready           (the plan is on screen)
  T2  claim -> first_lesson_ready      (the first lesson can be read)
  outline end, and cost by job kind, read from GenerationJob (log ``at``, ``cost_usd``)

The API must already run with the flags under test and ``SOCRAT_DEV_LOGIN_ENABLED=true``; this
script never starts one. It reads the same database as that API (``--db``) for the job logs.
Results go to ``--out`` as JSON lines and to stdout as a Markdown table for live-run-log.md.

  uv run --project services/api python scripts/dev/bench_claim_to_today.py \\
      --api http://127.0.0.1:8010 --db sqlite:///D:/SOCRAT/Socrat/.cache/bench.db --parallel 3

Costs real money on a real provider (about $0.5 per run measured on 2026-11-20).
"""

import argparse
import itertools
import json
import secrets
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
from sqlalchemy import create_engine, text

GOALS = {
    "sql": "I want to learn SQL for my college project",
    "exam": "Help me pass my GCSE chemistry exam in June",
    "music": "I want to learn to read sheet music for the piano",
}
MODES = ("sprint", "builder", "explorer")
MINUTES = (10, 25)
DONE = {"first_lesson_ready", "first_lesson_failed"}


def run_one(api: str, origin: str, goal: str, mode: str, minutes: int, timeout: int) -> dict:
    c = httpx.Client(base_url=api, timeout=600, headers={"Origin": origin})
    subject = f"bench-{secrets.token_hex(4)}"
    out: dict = dict(goal=goal, mode=mode, minutes=minutes, subject=subject)
    c.post("/api/v1/auth/dev-login", json={"subject": subject, "display_name": subject})
    h = {"X-CSRF-Token": c.get("/api/v1/me").json()["csrf_token"]}
    c.patch("/api/v1/me", json={"birth_year": 2000, "timezone": "UTC"}, headers=h)
    started = time.time()
    d = c.post("/api/v1/onboarding", json={"text": GOALS[goal]}, headers=h)
    if d.status_code != 200:
        return out | dict(error=f"onboarding {d.status_code}")
    draft = d.json()
    d = c.post(
        f"/api/v1/onboarding/{draft['id']}/choose",
        json={"mode": mode, "door": draft["doors"][0]},
        headers=h,
    ).json()
    out["calibration"] = d["calibration"]
    if d["calibration"] == "ready":
        for step in ("win", "snag"):
            task = d[step] or {}
            # In order: a miss (and so a Lesson 0 gap) happens whenever option 0 is not the key.
            for choice in range(len(task.get("options") or [])):
                a = c.post(
                    f"/api/v1/onboarding/{draft['id']}/answer",
                    json={"step": step, "choice": choice, "ms": 30000},
                    headers=h,
                ).json()
                d = a
                if a["result"]["done"]:
                    break
    out["lesson0_s"] = round(time.time() - started, 1)
    claimed = time.time()
    r = c.post(f"/api/v1/onboarding/{draft['id']}/claim", json={"minutes": minutes}, headers=h)
    if r.status_code != 200:
        return out | dict(error=f"claim {r.status_code}")
    rid = out["request"] = r.json()["request"]["id"]
    out["claimed_at"] = int(claimed)
    while time.time() - claimed < timeout:
        state = (c.get(f"/api/v1/learning-requests/{rid}").json().get("start") or {}).get("state")
        if state != "waiting" and "t1_s" not in out:
            out["t1_s"] = round(time.time() - claimed, 1)
        if state in DONE:
            out["t2_s" if state == "first_lesson_ready" else "failed_s"] = round(
                time.time() - claimed, 1
            )
            break
        time.sleep(3)
    else:
        out["error"] = "timeout"
    return out


def from_jobs(db_url: str, row: dict) -> dict:
    """Outline end and cost by job kind for this request's course, from the job log."""
    if "request" not in row:
        return row
    eng = create_engine(db_url)
    with eng.connect() as db:
        jobs = db.execute(
            text("select kind, course_id, input, log, cost_usd from generation_jobs")
        ).all()
    outline = next(
        (j for j in jobs if j.kind == "outline" and row["request"] in str(j.input)), None
    )
    if outline is None:
        return row
    course = outline.course_id
    costs: dict[str, float] = {}
    for j in jobs:
        if j.course_id == course:
            costs[j.kind] = round(costs.get(j.kind, 0.0) + (j.cost_usd or 0.0), 4)
    log = json.loads(outline.log) if isinstance(outline.log, str) else outline.log
    end = next(
        (e["at"] for e in log if e.get("event") in ("outline_saved", "outline_reused")), None
    )
    sizes = next((e for e in log if "modules" in e and "concepts" in e), {})
    return row | dict(
        course=course,
        outline_end_s=end - row["claimed_at"] if end else None,
        modules=sizes.get("modules"),
        concepts=sizes.get("concepts"),
        cost=costs,
        events=[e["event"] for e in log if "event" in e],
    )


def table(rows: list[dict]) -> str:
    head = (
        "| goal | mode | min | T1 s | T2 s | outline end s | outline $ | lessons $ | size | note |"
    )
    lines = [head, "|" + "---|" * 10]
    for r in rows:
        cost = r.get("cost", {})
        lines.append(
            f"| {r['goal']} | {r['mode']} | {r['minutes']} | {r.get('t1_s', '')} | "
            f"{r.get('t2_s', '')} | {r.get('outline_end_s', '')} | {cost.get('outline', '')} | "
            f"{cost.get('package', '')} | {r.get('modules', '')}/{r.get('concepts', '')} | "
            f"{r.get('error', '') or ('failed' if 'failed_s' in r else '')} |"
        )
    t2 = [r["t2_s"] for r in rows if "t2_s" in r]
    if t2:
        lines.append(
            f"\nT2 median {statistics.median(t2):.0f} s, max {max(t2):.0f} s, "
            f"{len(t2)}/{len(rows)} reached the first lesson."
        )
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://127.0.0.1:8010")
    ap.add_argument("--origin", default="http://localhost:3000")
    ap.add_argument("--db", required=True, help="the API's database URL, for the job logs")
    ap.add_argument("--goals", default=",".join(GOALS))
    ap.add_argument("--modes", default=",".join(MODES))
    ap.add_argument("--minutes", default=",".join(map(str, MINUTES)))
    ap.add_argument("--parallel", type=int, default=1)
    ap.add_argument("--timeout", type=int, default=1500, help="seconds per run after the claim")
    ap.add_argument("--out", default="bench-claim-to-today.jsonl")
    a = ap.parse_args()
    grid = list(
        itertools.product(a.goals.split(","), a.modes.split(","), map(int, a.minutes.split(",")))
    )
    with ThreadPoolExecutor(a.parallel) as pool:
        futures = [pool.submit(run_one, a.api, a.origin, g, m, n, a.timeout) for g, m, n in grid]
        rows = []
        for f in futures:
            try:
                rows.append(from_jobs(a.db, f.result()))
            except Exception as exc:  # one broken run must not lose the others
                rows.append(dict(goal="?", mode="?", minutes=0, error=str(exc)[:200]))
            with open(a.out, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rows[-1]) + "\n")
            print(json.dumps({k: rows[-1].get(k) for k in ("goal", "mode", "minutes", "t2_s")}))
    print(table(rows))


if __name__ == "__main__":
    main()
