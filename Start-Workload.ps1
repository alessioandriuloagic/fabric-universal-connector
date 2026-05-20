param (
    [ValidateSet("universal", "customer-insight-journey", "sales-crm", "business-central", "sql-db")]
    [string]$Workload = "universal",
    [switch]$NoDevServer,
    [switch]$NoDevGateway,
    [switch]$NoBackend,
    [boolean]$InteractiveLogin = $true
)

$ErrorActionPreference = "Stop"
$rootDir = $PSScriptRoot

$WorkloadLabel = if ($Workload -eq "universal") { "Universal Connector" } else { $Workload }
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Fabric Universal Connector - Local Dev Launcher" -ForegroundColor Cyan
Write-Host "  Workload: $WorkloadLabel" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

################################################
# Verify prerequisites
################################################
$workloadDir = Join-Path $rootDir "Workload"
if (-not (Test-Path (Join-Path $workloadDir "node_modules"))) {
    Write-Host "node_modules not found - running npm install..." -ForegroundColor Yellow
    Push-Location $workloadDir
    try { npm install } finally { Pop-Location }
}

################################################
# Start FastAPI backend (new window)
################################################
if (-not $NoBackend) {
    $backendDir = Join-Path $rootDir "backend"
    if (Test-Path $backendDir) {
        Write-Host "Starting FastAPI backend (http://localhost:8000)..." -ForegroundColor Green
        $backendCmd = "Set-Location '$backendDir'; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
        Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $backendCmd
        Write-Host "  FastAPI backend launched in a new window." -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host "  backend/ directory not found — skipping backend startup." -ForegroundColor Yellow
        Write-Host ""
    }
}

################################################
# Start webpack dev server (new window)
################################################
if (-not $NoDevServer) {
    Write-Host "Starting webpack dev server (workload: $Workload)..." -ForegroundColor Green
    $npmScript = if ($Workload -eq "universal") { "npm start" } else { "npm run `"start:$Workload`"" }
    $devCmd = "Set-Location '$workloadDir'; $npmScript"
    Start-Process powershell.exe -ArgumentList "-NoExit", "-Command", $devCmd
    Write-Host "  Webpack dev server launched in a new window." -ForegroundColor Green
    Write-Host ""
}

################################################
# Start DevGateway (this window)
################################################
if (-not $NoDevGateway) {
    Write-Host "Starting DevGateway (builds manifest first)..." -ForegroundColor Green
    $devGatewayScript = Join-Path $rootDir "scripts\Run\StartDevGateway.ps1"
    & $devGatewayScript -InteractiveLogin $InteractiveLogin
}