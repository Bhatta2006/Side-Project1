#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
command -v uv >/dev/null || { echo 'Install uv: python3 -m pip install uv==0.12.20'; exit 1; }
uv sync --frozen
test -d node_modules || npm ci
.venv/bin/python scripts/dev/prepare.py
eval "$(.venv/bin/python -c 'import json,shlex; from pathlib import Path; print("\n".join("export "+k+"="+shlex.quote(json.loads(v)) for k,v in (line.split("=",1) for line in Path(".env.local").read_text().splitlines())))')"
export PYTHONPATH="$PWD/services/api/src:$PWD/services/execution/src"
.venv/bin/alembic upgrade head
.venv/bin/python scripts/content/build.py
test "${1:-}" != '--prepare-only' || exit 0
pids=()
trap 'for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done; wait || true' EXIT INT TERM
.venv/bin/python -m uvicorn socrat.main:create_app --factory --host 127.0.0.1 --port 8000 >.cache/native-api.log 2>&1 & pids+=("$!")
for n in $(seq 1 90); do curl -fsS http://127.0.0.1:8000/api/health/ready >/dev/null 2>&1 && break; sleep 1; done
curl -fsS http://127.0.0.1:8000/api/health/ready >/dev/null
.venv/bin/python -m runner.worker >.cache/native-worker.log 2>&1 & pids+=("$!")
.venv/bin/python -m socrat.worker >.cache/native-jobs.log 2>&1 & pids+=("$!")  # outbox and Playground generations
node apps/web/scripts/copy-runtimes.mjs
node node_modules/next/dist/bin/next dev apps/web --hostname 127.0.0.1 --port 3000 >.cache/native-web.log 2>&1 & pids+=("$!")
for n in $(seq 1 120); do curl -fsS http://localhost:3000 >/dev/null 2>&1 && break; sleep 1; done
curl -fsS http://localhost:3000 >/dev/null
echo 'Native demo ready: http://localhost:3000 — no Docker or WSL required.'
wait -n "${pids[@]}"
