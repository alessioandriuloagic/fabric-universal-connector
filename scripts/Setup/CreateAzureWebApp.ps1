param (
    [Parameter(Mandatory = $true)]
    [string]$AppName,

    [Parameter(Mandatory = $true)]
    [string]$ResourceGroupName,

    [string]$Location = "westeurope",
    [string]$SubscriptionId
)

$ErrorActionPreference = "Continue"

function Invoke-Az {
    param([string[]]$Args)
    $output = & az @Args 2>$null
    return $output
}

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Fabric Universal Connector - Azure Static Web App Setup" -ForegroundColor Cyan
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
    Write-Host "Switching to subscription $SubscriptionId..." -ForegroundColor Yellow
    az account set --subscription $SubscriptionId
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to switch subscription."; exit 1 }
}

Write-Host ""

################################################
# Register provider (idempotent)
################################################
Write-Host "Step 1/3 - Registering Microsoft.Web provider..." -ForegroundColor Yellow
az provider register --namespace Microsoft.Web | Out-Null
Write-Host "  Done." -ForegroundColor Green

################################################
# Resource Group
################################################
Write-Host "Step 2/3 - Resource Group '$ResourceGroupName'..." -ForegroundColor Yellow

Invoke-Az @("group", "show", "--name", $ResourceGroupName) | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Already exists - skipping." -ForegroundColor Cyan
} else {
    az group create --name $ResourceGroupName --location $Location | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create resource group."; exit 1 }
    Write-Host "  Created in $Location." -ForegroundColor Green
}

################################################
# Static Web App
################################################
Write-Host "Step 3/3 - Static Web App '$AppName'..." -ForegroundColor Yellow

Invoke-Az @("staticwebapp", "show", "--name", $AppName, "--resource-group", $ResourceGroupName) | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Already exists - skipping." -ForegroundColor Cyan
} else {
    az staticwebapp create `
        --name $AppName `
        --resource-group $ResourceGroupName `
        --location $Location `
        --sku Free | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create Static Web App."; exit 1 }
    Write-Host "  Created." -ForegroundColor Green
}

################################################
# Retrieve hostname
################################################
$hostJson = Invoke-Az @("staticwebapp", "show", "--name", $AppName, "--resource-group", $ResourceGroupName, "--query", "defaultHostname", "--output", "tsv")
$hostname = ($hostJson | Out-String).Trim()
$webappUrl = "https://$hostname"

################################################
# Summary
################################################
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  Setup completed!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Static Web App URL : $webappUrl" -ForegroundColor Cyan
Write-Host "  Resource Group     : $ResourceGroupName" -ForegroundColor Cyan
Write-Host "  SKU                : Free" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next - update Workload\.env.prod:" -ForegroundColor Yellow
Write-Host "  FRONTEND_URL=$webappUrl" -ForegroundColor White
Write-Host ""
Write-Host "Then run:" -ForegroundColor Yellow
Write-Host "  .\scripts\Build\BuildRelease.ps1 -FrontendAppId <App-ID> -Environment prod" -ForegroundColor White
Write-Host "  .\scripts\Deploy\DeployToStaticWebApp.ps1 -AppName $AppName -ResourceGroupName $ResourceGroupName" -ForegroundColor White