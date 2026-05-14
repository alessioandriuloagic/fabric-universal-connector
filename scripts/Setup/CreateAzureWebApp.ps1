param (
    [Parameter(Mandatory = $true)]
    [string]$WebAppName,

    [Parameter(Mandatory = $true)]
    [string]$ResourceGroupName,

    [string]$Location = "westeurope",
    [string]$AppServicePlanName,
    [ValidateSet("F1", "B1", "B2", "B3", "S1", "S2", "P1v3")]
    [string]$Sku = "B1",
    [string]$SubscriptionId
)

# Use Continue so native az errors don't stop the script; we check $LASTEXITCODE instead
$ErrorActionPreference = "Continue"

if (-not $AppServicePlanName) {
    $AppServicePlanName = "$WebAppName-plan"
}

function Invoke-Az {
    param([string[]]$Args)
    $output = & az @Args 2>$null
    return $output
}

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Fabric Universal Connector - Azure Web App Setup" -ForegroundColor Cyan
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
# Resource Group
################################################
Write-Host "Step 1/4 - Resource Group '$ResourceGroupName'..." -ForegroundColor Yellow

Invoke-Az @("group", "show", "--name", $ResourceGroupName) | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Already exists - skipping." -ForegroundColor Cyan
} else {
    az group create --name $ResourceGroupName --location $Location | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create resource group."; exit 1 }
    Write-Host "  Created in $Location." -ForegroundColor Green
}

################################################
# App Service Plan
################################################
Write-Host "Step 2/4 - App Service Plan '$AppServicePlanName' (SKU: $Sku)..." -ForegroundColor Yellow

Invoke-Az @("appservice", "plan", "show", "--name", $AppServicePlanName, "--resource-group", $ResourceGroupName) | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Already exists - skipping." -ForegroundColor Cyan
} else {
    az appservice plan create --name $AppServicePlanName --resource-group $ResourceGroupName --sku $Sku | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create App Service Plan."; exit 1 }
    Write-Host "  Created." -ForegroundColor Green
}

################################################
# Web App
################################################
Write-Host "Step 3/4 - Web App '$WebAppName'..." -ForegroundColor Yellow

Invoke-Az @("webapp", "show", "--name", $WebAppName, "--resource-group", $ResourceGroupName) | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Already exists - skipping." -ForegroundColor Cyan
} else {
    az webapp create --name $WebAppName --resource-group $ResourceGroupName --plan $AppServicePlanName | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create Web App."; exit 1 }
    Write-Host "  Created." -ForegroundColor Green
}

################################################
# CORS
################################################
Write-Host "Step 4/4 - Configuring CORS..." -ForegroundColor Yellow

$corsOrigins = @(
    "https://app.fabric.microsoft.com",
    "https://app.powerbi.com",
    "https://msit.fabric.microsoft.com",
    "https://msit.powerbi.com"
)

foreach ($origin in $corsOrigins) {
    az webapp cors add --name $WebAppName --resource-group $ResourceGroupName --allowed-origins $origin | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  WARNING: could not add CORS for $origin" -ForegroundColor Yellow
    } else {
        Write-Host "  CORS allowed: $origin" -ForegroundColor Green
    }
}

################################################
# Summary
################################################
$webappUrl = "https://$WebAppName.azurewebsites.net"

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  Setup completed!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Web App URL      : $webappUrl" -ForegroundColor Cyan
Write-Host "  Resource Group   : $ResourceGroupName" -ForegroundColor Cyan
Write-Host "  App Service Plan : $AppServicePlanName ($Sku)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next - update Workload\.env.prod:" -ForegroundColor Yellow
Write-Host "  FRONTEND_URL=$webappUrl" -ForegroundColor White
Write-Host ""
Write-Host "Then run:" -ForegroundColor Yellow
Write-Host "  .\scripts\Build\BuildRelease.ps1 -FrontendAppId <App-ID> -Environment prod" -ForegroundColor White
Write-Host "  .\scripts\Deploy\DeployToAzureWebApp.ps1 -WebAppName $WebAppName -ResourceGroupName $ResourceGroupName" -ForegroundColor White