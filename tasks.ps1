<#
.SYNOPSIS
    ASCIIP PowerShell task runner — Windows-native equivalent of the Makefile.

.DESCRIPTION
    Provides the same task set the Makefile exposes on Unix, for operators who
    cannot or prefer not to install GNU Make on Windows.

.EXAMPLE
    ./tasks.ps1 bootstrap
    ./tasks.ps1 up
    ./tasks.ps1 test
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Task = 'help',

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = 'Stop'
$script:ApiHost = if ($env:API_HOST) { $env:API_HOST } else { '0.0.0.0' }
$script:ApiPort = if ($env:API_PORT) { $env:API_PORT } else { '8000' }
$script:WebPort = if ($env:WEB_PORT) { $env:WEB_PORT } else { '3000' }

function Require-Tool($name, $hint) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Write-Error "$name is required. $hint"
    }
}

function Invoke-Prereqs {
    Require-Tool 'python' 'Install Python 3.11.'
    Require-Tool 'uv'     'Install via: winget install astral-sh.uv  (or: pip install uv)'
    Require-Tool 'node'   'Install Node 20 LTS.'
    Require-Tool 'pnpm'   'Install via: npm i -g pnpm'
    Write-Host 'all prerequisites present' -ForegroundColor Green
}

function Invoke-Bootstrap {
    Invoke-Prereqs
    uv sync --all-extras
    pnpm install
    try { uv run python -m asciip_data_pipeline.bootstrap --seed-from-snapshots } catch { Write-Warning $_ }
    Write-Host "bootstrap complete. run './tasks.ps1 up' to start services." -ForegroundColor Green
}

function Invoke-Env {
    if (-not (Test-Path .env)) { Copy-Item .env.example .env }
    Write-Host '.env is ready. edit to enable live data sources.'
}

function Invoke-Up {
    Invoke-Env
    Write-Host "starting api on :$ApiPort and web on :$WebPort" -ForegroundColor Cyan
    $apiArgs = "run uvicorn asciip_api.main:app --host $ApiHost --port $ApiPort --reload"
    $webArgs = "--filter @asciip/web dev -- --port $WebPort"
    $api = Start-Process uv -ArgumentList $apiArgs -PassThru -NoNewWindow
    $web = Start-Process pnpm -ArgumentList $webArgs -PassThru -NoNewWindow
    try {
        Wait-Process -Id $api.Id, $web.Id
    } finally {
        foreach ($p in @($api, $web)) {
            if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
        }
    }
}

function Invoke-Api     { uv run uvicorn asciip_api.main:app --host $ApiHost --port $ApiPort --reload }
function Invoke-Web     { pnpm --filter @asciip/web dev -- --port $WebPort }
function Invoke-Ingest  { uv run python -m asciip_data_pipeline.orchestrator }
function Invoke-Features { uv run python -m asciip_data_pipeline.features.build }
function Invoke-Train   { uv run python -m asciip_ml_models.train_all }

function Invoke-Lint {
    uv run ruff check .
    pnpm run -r lint
}

function Invoke-Format {
    uv run ruff format .
    pnpm run format
}

function Invoke-Typecheck {
    uv run mypy .
    pnpm run typecheck
}

function Invoke-Test {
    uv run pytest -m "not e2e" --cov --cov-report=term-missing --cov-report=xml
}

function Invoke-E2E    { pnpm --filter @asciip/web exec playwright test }
function Invoke-Smoke  { uv run python -m asciip_api.smoke }

function Invoke-Clean {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue .ruff_cache, .mypy_cache, .pytest_cache, coverage.xml, htmlcov, .turbo
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue apps/web/.next, apps/web/.turbo
    Get-ChildItem -Recurse -Directory -Filter __pycache__ -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
}

function Invoke-ResetData {
    foreach ($d in 'data/raw', 'data/features', 'data/exports') {
        if (Test-Path $d) { Remove-Item -Recurse -Force $d }
        New-Item -ItemType Directory -Path $d | Out-Null
    }
    Write-Host "data reset. run './tasks.ps1 bootstrap' to reseed from snapshots."
}

function Invoke-Help {
    @"
ASCIIP — Apple Supply Chain Impact Intelligence Platform

Usage: ./tasks.ps1 <task>

Setup
  prereqs        Verify python, uv, node, pnpm present
  bootstrap      First-run: install deps, seed DuckDB from snapshots
  env            Create .env from .env.example if missing

Local dev
  up             Start api + web
  api            Start only FastAPI (autoreload)
  web            Start only Next.js

Data and models
  ingest         Run ingestion pipeline once
  features       Rebuild feature store views
  train          Retrain all ML models

Quality
  lint           ruff + eslint
  format         ruff format + prettier
  typecheck      mypy --strict + tsc --noEmit
  test           unit + property + integration w/ coverage
  e2e            Playwright end-to-end
  smoke          Post-deploy health check

Housekeeping
  clean          Remove caches and build artifacts
  reset-data     Wipe data/raw, data/features, data/exports
"@
}

$ErrorActionPreference = 'Stop'
switch ($Task.ToLowerInvariant()) {
    'help'       { Invoke-Help }
    'prereqs'    { Invoke-Prereqs }
    'bootstrap'  { Invoke-Bootstrap }
    'env'        { Invoke-Env }
    'up'         { Invoke-Up }
    'api'        { Invoke-Api }
    'web'        { Invoke-Web }
    'ingest'     { Invoke-Ingest }
    'features'   { Invoke-Features }
    'train'      { Invoke-Train }
    'lint'       { Invoke-Lint }
    'format'     { Invoke-Format }
    'typecheck'  { Invoke-Typecheck }
    'test'       { Invoke-Test }
    'e2e'        { Invoke-E2E }
    'smoke'      { Invoke-Smoke }
    'clean'      { Invoke-Clean }
    'reset-data' { Invoke-ResetData }
    default      { Invoke-Help; Write-Error "Unknown task: $Task" }
}
