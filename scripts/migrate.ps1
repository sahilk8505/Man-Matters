# =============================================================================
# migrate.ps1 - Man Matters Creative OS
# Runs all DB migrations. Run from project root: .\scripts\migrate.ps1
# Requires: Docker Desktop running + docker compose up db backend already started
# =============================================================================

$ErrorActionPreference = "Continue"
$PROJECT_ROOT = Split-Path -Parent $PSScriptRoot

Set-Location $PROJECT_ROOT

Write-Host ""
Write-Host "============================================" -ForegroundColor Blue
Write-Host "  Man Matters COS - Database Migration" -ForegroundColor Blue
Write-Host "============================================" -ForegroundColor Blue
Write-Host ""

# ---------------------------------------------------------------------------
# Step 1: Wait for PostgreSQL to be ready
# ---------------------------------------------------------------------------
Write-Host "[1/4] Waiting for PostgreSQL..." -ForegroundColor Yellow

$ready = $false
for ($i = 1; $i -le 30; $i++) {
    $out = docker compose exec -T db pg_isready -U postgres 2>&1
    if ($LASTEXITCODE -eq 0) {
        $ready = $true
        break
    }
    Write-Host "      Attempt $i/30 - retrying in 3s..." -ForegroundColor DarkGray
    Start-Sleep 3
}

if (-not $ready) {
    Write-Host ""
    Write-Host "  ERROR: Database did not become ready." -ForegroundColor Red
    Write-Host "  Make sure Docker is running and the stack is up:" -ForegroundColor Red
    Write-Host "  > docker compose up db redis backend worker scheduler" -ForegroundColor Red
    exit 1
}
Write-Host "  PostgreSQL is ready." -ForegroundColor Green

# ---------------------------------------------------------------------------
# Step 2: Copy migration files into the DB container
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[2/4] Copying migration files into container..." -ForegroundColor Yellow
docker compose cp "supabase/migrations/." db:/migrations/
Write-Host "  Done." -ForegroundColor Green

# ---------------------------------------------------------------------------
# Step 3: Run migrations in order
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[3/4] Running migrations..." -ForegroundColor Yellow

$migrations = @(
    "001_extensions_and_enums.sql",
    "002_core_tables.sql",
    "003_metrics_and_scores.sql",
    "004_ai_tables.sql",
    "005_functions_and_views.sql",
    "006_seed.sql"
)

foreach ($file in $migrations) {
    Write-Host "      -> $file" -ForegroundColor Cyan
    docker compose exec -T db psql -U postgres -d man_matters_cos -f "/migrations/$file" -v ON_ERROR_STOP=1 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "  FAILED on $file. Check the error above." -ForegroundColor Red
        exit 1
    }
    Write-Host "         OK" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# Step 4: Verify seed data
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[4/4] Verifying seed data..." -ForegroundColor Yellow
$count = docker compose exec -T db psql -U postgres -d man_matters_cos -t -c "SELECT COUNT(*) FROM products;" 2>&1
Write-Host "      Products seeded: $($count.Trim())" -ForegroundColor Cyan
$ucount = docker compose exec -T db psql -U postgres -d man_matters_cos -t -c "SELECT COUNT(*) FROM users;" 2>&1
Write-Host "      Users seeded:    $($ucount.Trim())" -ForegroundColor Cyan

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  All migrations complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Login at: http://localhost:3001/login" -ForegroundColor White
Write-Host "  Email:    admin@manmatters.com" -ForegroundColor White
Write-Host "  Password: secret  (change after first login)" -ForegroundColor White
Write-Host ""
Write-Host "  API docs: http://localhost:8001/docs" -ForegroundColor DarkGray
Write-Host ""
