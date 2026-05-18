param (
    [Parameter(Mandatory = $true)]
    [string]$AppName,

    [Parameter(Mandatory = $true)]
    [string]$ResourceGroupName,

    [string]$Location = "westeurope",
    [string]$SubscriptionId
)

$ErrorActionPreference = "Continue"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Fabric Universal Connector - Azure Static Web App Setup" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

################################################
# Verify Azure CLI + login
# --only-show-errors suppresses warnings (e.g. upgrade notices) without
# 2>$null, which in PS5.1 mixes stderr into stdout and breaks ConvertFrom-Json
################################################
& az --version --only-show-errors | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Azure CLI not found. Install from: https://docs.microsoft.com/cli/azure/install-azure-cli"
    exit 1
}

$accountJson = az account show --output json --only-show-errors
if ($LASTEXITCODE -ne 0 -or -not $accountJson) {
    Write-Host "Not logged in - running az login..." -ForegroundColor Yellow
    az login --only-show-errors
    $accountJson = az account show --output json --only-show-errors
}

$account = $accountJson | ConvertFrom-Json
Write-Host "Logged in as  : $($account.user.name)" -ForegroundColor Green
Write-Host "Subscription  : $($account.name) ($($account.id))" -ForegroundColor Green

if ($SubscriptionId -and $account.id -ne $SubscriptionId) {
    Write-Host "Switching to subscription $SubscriptionId..." -ForegroundColor Yellow
    az account set --subscription $SubscriptionId --only-show-errors
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to switch subscription."; exit 1 }
}

Write-Host ""

################################################
# Register provider (idempotent)
################################################
Write-Host "Step 1/3 - Registering Microsoft.Web provider..." -ForegroundColor Yellow
az provider register --namespace Microsoft.Web --only-show-errors | Out-Null
Write-Host "  Done." -ForegroundColor Green

################################################
# Resource Group
################################################
Write-Host "Step 2/3 - Resource Group '$ResourceGroupName'..." -ForegroundColor Yellow

az group show --name $ResourceGroupName --only-show-errors | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Already exists - skipping." -ForegroundColor Cyan
} else {
    az group create --name $ResourceGroupName --location $Location --only-show-errors | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create resource group."; exit 1 }
    Write-Host "  Created in $Location." -ForegroundColor Green
}

################################################
# Static Web App
################################################
Write-Host "Step 3/3 - Static Web App '$AppName'..." -ForegroundColor Yellow

az staticwebapp show --name $AppName --resource-group $ResourceGroupName --only-show-errors | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Already exists - skipping." -ForegroundColor Cyan
} else {
    az staticwebapp create `
        --name $AppName `
        --resource-group $ResourceGroupName `
        --location $Location `
        --sku Free `
        --only-show-errors | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create Static Web App."; exit 1 }
    Write-Host "  Created." -ForegroundColor Green
}

################################################
# Retrieve hostname
################################################
$hostname = az staticwebapp show `
    --name $AppName `
    --resource-group $ResourceGroupName `
    --query "defaultHostname" `
    --output tsv `
    --only-show-errors

$hostname = ($hostname | Out-String).Trim()
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