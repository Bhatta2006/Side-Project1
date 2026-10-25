param([switch]$PrepareOnly, [switch]$SkipPersonas)
$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path "$PSScriptRoot/../..")
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw 'Install uv: python -m pip install uv==0.12.20' }
uv sync --frozen
if ($LASTEXITCODE) { throw 'Locked Python dependency installation failed' }
if (-not (Test-Path node_modules)) { npm.cmd ci; if ($LASTEXITCODE) { throw 'Node dependency installation failed' } }
& .venv/Scripts/python.exe scripts/dev/prepare.py
if ($LASTEXITCODE) { throw 'Configuration generation failed' }
foreach ($line in Get-Content .env.local) {
  $pair = $line.Split('=', 2)
  [Environment]::SetEnvironmentVariable($pair[0], ($pair[1] | ConvertFrom-Json), 'Process')
}
$env:PYTHONPATH = "$(Get-Location)/services/api/src;$(Get-Location)/services/execution/src"
& .venv/Scripts/alembic.exe upgrade head
if ($LASTEXITCODE) { throw 'Database migration failed' }
& .venv/Scripts/python.exe scripts/content/build.py
if ($LASTEXITCODE) { throw 'Course content build failed' }
if ($PrepareOnly) { exit 0 }
$children = @()
try {
  foreach ($port in 8000, 3000) { if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) { throw "Port $port is in use. Stop that project's server before starting the demo." } }
  $children += Start-Process -FilePath '.venv/Scripts/python.exe' -ArgumentList '-m uvicorn socrat.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log --loop socrat.dev_loop:loop_factory' -WindowStyle Hidden -PassThru -RedirectStandardOutput .cache/native-api.log -RedirectStandardError .cache/native-api-error.log
  $deadline = (Get-Date).AddSeconds(90)
  do {
    try { $ready = Invoke-RestMethod 'http://127.0.0.1:8000/api/health/ready' -TimeoutSec 2 } catch { $ready = $null }
    if ((Get-Date) -gt $deadline) { throw 'API health timed out; inspect .cache/native-api-error.log' }
    if (-not $ready) { Start-Sleep -Milliseconds 400 }
  } until ($ready)
  $children += Start-Process -FilePath '.venv/Scripts/python.exe' -ArgumentList '-m runner.worker' -WindowStyle Hidden -PassThru -RedirectStandardOutput .cache/native-worker.log -RedirectStandardError .cache/native-worker-error.log
  node apps/web/scripts/copy-runtimes.mjs; if ($LASTEXITCODE) { throw 'Copying the browser code runtimes failed' }
  $children += Start-Process -FilePath (Get-Command node).Source -ArgumentList 'node_modules/next/dist/bin/next dev apps/web --hostname 127.0.0.1 --port 3000' -WindowStyle Hidden -PassThru -RedirectStandardOutput .cache/native-web.log -RedirectStandardError .cache/native-web-error.log
  $deadline = (Get-Date).AddSeconds(120)
  do {
    try { $webReady = (Invoke-WebRequest 'http://localhost:3000' -TimeoutSec 5 -UseBasicParsing).StatusCode -eq 200 } catch { $webReady = $false }
    if ((Get-Date) -gt $deadline) { throw 'Web health timed out; inspect .cache/native-web-error.log' }
    if (-not $webReady) { Start-Sleep -Milliseconds 500 }
  } until ($webReady)
  Write-Host 'Native demo ready: http://localhost:3000 — no Docker or WSL required. Ctrl+C stops these demo processes.'
  $apiMisses = 0
  $nextProbe = Get-Date
  while ($true) {
    foreach ($child in $children) { if ($child.HasExited) { throw 'A demo process stopped; inspect .cache/native-*.log' } }
    if ((Get-Date) -ge $nextProbe) {
      try { $apiAlive = (Invoke-WebRequest 'http://127.0.0.1:8000/api/health/live' -TimeoutSec 3 -UseBasicParsing).StatusCode -eq 200 } catch { $apiAlive = $false }
      if ($apiAlive) { $apiMisses = 0 } else { $apiMisses++ }
      if ($apiMisses -ge 3) { throw 'API stopped responding; inspect .cache/native-api-error.log' }
      $nextProbe = (Get-Date).AddSeconds(10)
    }
    Start-Sleep -Seconds 2
  }
} finally {
  foreach ($child in $children) { if (-not $child.HasExited) { taskkill.exe /PID $child.Id /T /F | Out-Null } }
}
