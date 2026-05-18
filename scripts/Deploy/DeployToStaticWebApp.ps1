param (
    [Parameter(Mandatory = $true)]
    [string]$AppName,

    [Parameter(Mandatory = $true)]
    [string]$ResourceGroupName,

    [string]$ReleasePath = "..\..\release\app",
    [string]$SubscriptionId
)

$ErrorActionPreference = "Continue"

function Invoke-Az {
    param([string[]]$Args)
    $output = & az @Args 2>$null
    return $output
}

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Fabric Universal Connector - Deploy to Static Web App" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

################################################
# Verify Azure CLI + login
################################################
& az --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Azure CLI not found. Install from: https://docs.microsoft.com/cli/azure/install-azure-cli"
    exit 1
}

$accountJson = Invoke-Az @("account", "show")
if ($LASTEXITCODE -ne 0 -or -not $accountJson) {
    Write-Host "Not logged in - running az login..." -ForegroundColor Yellow
    az login
    $accountJson = Invoke-Az @("account", "show")
}

$account = $accountJson | ConvertFrom-Json
Write-Host "Logged in as  : $($account.user.name)" -ForegroundColor Green
Write-Host "Subscription  : $($account.name) ($($account.id))" -ForegroundColor Green

if ($SubscriptionId -and $account.id -ne $SubscriptionId) {
    az account set --subscription $SubscriptionId
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to switch subscription."; exit 1 }
}

Write-Host ""

################################################
# Validate release directory
################################################
$fullReleasePath = Join-Path $PSScriptRoot $ReleasePath
if (-not (Test-Path $fullReleasePath)) {
    Write-Error "Release directory not found: $fullReleasePath"
    Write-Host "Run first: .\scripts\Build\BuildRelease.ps1 -Environment prod" -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path (Join-Path $fullReleasePath "index.html"))) {
    Write-Error "index.html not found in $fullReleasePath — build may have failed."
    exit 1
}
Write-Host "Release directory: $fullReleasePath" -ForegroundColor Green

################################################
# Retrieve deployment token
################################################
Write-Host ""
Write-Host "Step 1/3 - Retrieving deployment token..." -ForegroundColor Yellow

$tokenJson = Invoke-Az @("staticwebapp", "secrets", "list", "--name", $AppName, "--resource-group", $ResourceGroupName, "--query", "properties.apiKey", "--output", "tsv")
$deployToken = ($tokenJson | Out-String).Trim()

if (-not $deployToken) {
    Write-Error "Could not retrieve deployment token for '$AppName'. Check that the Static Web App exists."
    exit 1
}
Write-Host "  Token retrieved." -ForegroundColor Green

################################################
# Ensure SWA CLI is available
################################################
Write-Host "Step 2/3 - Checking SWA CLI..." -ForegroundColor Yellow

& swa --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  SWA CLI not found - installing globally..." -ForegroundColor Yellow
    npm install -g @azure/static-web-apps-cli | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to install SWA CLI."; exit 1 }
}
Write-Host "  SWA CLI ready." -ForegroundColor Green

################################################
# Deploy
################################################
Write-Host "Step 3/3 - Deploying to Static Web App '$AppName'..." -ForegroundColor Yellow

swa deploy $fullReleasePath --deployment-token $deployToken --env production
if ($LASTEXITCODE -ne 0) {
    Write-Error "Deployment failed."
    exit 1
}

################################################
# Retrieve URL and summary
################################################
$hostJson = Invoke-Az @("staticwebapp", "show", "--name", $AppName, "--resource-group", $ResourceGroupName, "--query", "defaultHostname", "--output", "tsv")
$hostname = ($hostJson | Out-String).Trim()
$webappUrl = "https://$hostname"

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  Deployment completed!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  URL : $webappUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Verify the app loads: $webappUrl" -ForegroundColor White
Write-Host "  2. Upload the manifest .nupkg to Fabric Admin Portal" -ForegroundColor White
Write-Host "     -> Admin Portal -> Workloads -> Upload package" -ForegroundColor White