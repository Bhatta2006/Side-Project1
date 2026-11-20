# Live API for scripts/dev/journey.mjs: real model (key and provider from .env), a fresh database,
# dev login, and the main-path generation flags. Run from the repo root; needs port 8000 free.
# Pair with `npm run dev` (port 3000).
# -Keep keeps the database between starts (manual testing as a learner).
param([string]$Db = ".cache/journey/journey.db", [switch]$Keep)
New-Item -ItemType Directory -Force (Split-Path $Db) | Out-Null
if (-not $Keep) { foreach ($s in '', '-wal', '-shm') { Remove-Item "$Db$s" -ErrorAction SilentlyContinue } }
$env:SOCRAT_ENVIRONMENT = 'development'
$env:SOCRAT_DATABASE_URL = "sqlite:///$((Resolve-Path .).Path.Replace('\','/'))/$Db"
$env:SOCRAT_DEV_LOGIN_ENABLED = 'true'
$env:SOCRAT_PUBLIC_ORIGIN = 'http://localhost:3000'
$env:SOCRAT_GEN_LEARNER_PLAN = 'true'
$env:SOCRAT_GEN_LEARNER_BRIEF = 'true'
$env:SOCRAT_GEN_WAITING_LEARNER = 'true'
$env:SOCRAT_SESSION_ONE_ADAPTATION = 'true'
$env:SOCRAT_ONBOARDING_PER_HOUR = '1000'
.venv/Scripts/alembic.exe upgrade head
if ($?) {
  .venv/Scripts/uvicorn.exe socrat.main:create_app --factory --app-dir services/api/src --host 127.0.0.1 --port 8000 --loop socrat.dev_loop:loop_factory
}
