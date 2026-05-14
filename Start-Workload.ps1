param (
    [switch]$NoDevServer,
    [switch]$NoDevGateway,
    [boolean]$InteractiveLogin = $true
)

$ErrorActionPreference = "Stop"
$rootDir = $PSScriptRoot

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Fabric Universal Connector - Local Dev Launcher" -ForegroundColor Cyan
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
# Start webpack dev server (new window)
################################################
if (-not $NoDevServer) {
    Write-Host "Starting webpack dev server (http://localhost:3000)..." -ForegroundColor Green
    $devServerScript = Join-Path $rootDir "scripts\Run\StartDevServer.ps1"
    Start-Process powershell.exe -ArgumentList "-NoExit", "-File", "`"$devServerScript`""
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