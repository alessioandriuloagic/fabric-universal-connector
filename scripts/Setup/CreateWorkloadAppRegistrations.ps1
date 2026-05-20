param (
    # Entra tenant where the workload dev/prod instance lives
    [string]$TenantId,

    # Prefix for the Fabric workload name (must be "Org" for production submissions)
    [string]$WorkloadNamePrefix = "Org",

    # Create a 180-day client secret for each App Registration
    [switch]$CreateSecret,

    # Restrict to specific workload IDs (default: create all 4)
    [ValidateSet("customer-insight-journey", "sales-crm", "business-central", "sql-db")]
    [string[]]$TargetWorkloads = @("customer-insight-journey", "sales-crm", "business-central", "sql-db")
)

Set-StrictMode -Off
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

# ── Workload catalogue ────────────────────────────────────────────────────────

$WorkloadCatalogue = @(
    @{
        WorkloadId     = "customer-insight-journey"
        WorkloadName   = ""    # filled below after prefix is known
        DisplayName    = "Customer Insight Journey — Frontend"
        FrontendUrl    = "https://cij.connector.agic.technology"
        EnvExamplePath = "workloads\customer-insight-journey\config\env.example"
    },
    @{
        WorkloadId     = "sales-crm"
        WorkloadName   = ""
        DisplayName    = "Sales CRM — Frontend"
        FrontendUrl    = "https://salescrm.connector.agic.technology"
        EnvExamplePath = "workloads\sales-crm\config\env.example"
    },
    @{
        WorkloadId     = "business-central"
        WorkloadName   = ""
        DisplayName    = "Business Central — Frontend"
        FrontendUrl    = "https://bc.connector.agic.technology"
        EnvExamplePath = "workloads\business-central\config\env.example"
    },
    @{
        WorkloadId     = "sql-db"
        WorkloadName   = ""
        DisplayName    = "SQL DB — Frontend"
        FrontendUrl    = "https://sqldb.connector.agic.technology"
        EnvExamplePath = "workloads\sql-db\config\env.example"
    }
)

$WorkloadNameMap = @{
    "customer-insight-journey" = "CustomerInsightJourney"
    "sales-crm"                = "SalesCRM"
    "business-central"         = "BusinessCentral"
    "sql-db"                   = "SqlDb"
}

# ── Helpers ───────────────────────────────────────────────────────────────────

function Invoke-GraphPost {
    param ([string]$Url, [string]$Body)
    $tmp = [System.IO.Path]::GetTempFileName()
    $Body | Out-File -FilePath $tmp -Encoding utf8
    $result = az rest --method POST --url $Url --headers "Content-Type=application/json" --body "@$tmp"
    Remove-Item $tmp -Force
    return $result
}

# ── Pre-flight ────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Fabric Universal Connector — App Registration Setup" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "  This script creates one Entra App Registration per workload frontend." -ForegroundColor White
Write-Host "  The shared backend App Registration is NOT created here." -ForegroundColor DarkGray
Write-Host ""

Write-Host "  Signing in to Azure CLI..." -ForegroundColor Yellow
az login --allow-no-subscriptions | Out-Null

if (-not $TenantId) {
    $TenantId = Read-Host "Enter your Fabric tenant ID"
}

$selectedWorkloads = $WorkloadCatalogue | Where-Object { $TargetWorkloads -contains $_.WorkloadId }

# Resolve WorkloadName for each selected workload
foreach ($w in $selectedWorkloads) {
    $w.WorkloadName = "$WorkloadNamePrefix.$($WorkloadNameMap[$w.WorkloadId])"
}

Write-Host ""
Write-Host "  Tenant ID  : $TenantId" -ForegroundColor DarkGray
Write-Host "  Prefix     : $WorkloadNamePrefix" -ForegroundColor DarkGray
Write-Host "  Workloads  : $($selectedWorkloads.WorkloadId -join ', ')" -ForegroundColor DarkGray
Write-Host ""

# ── Create one App Registration per workload ──────────────────────────────────

$results = @()

foreach ($w in $selectedWorkloads) {
    Write-Host "──────────────────────────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host "  Creating: $($w.DisplayName)" -ForegroundColor Yellow
    Write-Host "    WorkloadName : $($w.WorkloadName)" -ForegroundColor DarkGray
    Write-Host "    FrontendUrl  : $($w.FrontendUrl)" -ForegroundColor DarkGray

    $randomString = -join ((65..90) + (97..122) | Get-Random -Count 5 | ForEach-Object { [char]$_ })
    $appIdUri     = "api://localdevinstance/$TenantId/$($w.WorkloadName)/$randomString"

    $appBody = @{
        displayName    = $w.DisplayName
        signInAudience = "AzureADMultipleOrgs"
        optionalClaims = @{
            accessToken = @(@{ essential = $false; name = "idtyp" })
        }
        spa = @{
            redirectUris = @(
                "http://localhost:60006/close"
                "https://app.powerbi.com/workloadSignIn/$TenantId/$($w.WorkloadName)"
                "https://app.fabric.microsoft.com/workloadSignIn/$TenantId/$($w.WorkloadName)"
                "https://msit.powerbi.com/workloadSignIn/$TenantId/$($w.WorkloadName)"
                "https://msit.fabric.microsoft.com/workloadSignIn/$TenantId/$($w.WorkloadName)"
            )
        }
        identifierUris       = @($appIdUri)
        requiredResourceAccess = @(
            @{
                resourceAppId  = "00000009-0000-0000-c000-000000000000"   # Power BI / Fabric Service
                resourceAccess = @(
                    @{ id = "7ba630b9-8110-4e27-8d17-81e5f2218787"; type = "Scope" }  # Fabric.Extend
                )
            }
        )
    } | ConvertTo-Json -Compress -Depth 10

    $createResult = Invoke-GraphPost -Url "https://graph.microsoft.com/v1.0/applications" -Body $appBody
    $app = $createResult | ConvertFrom-Json

    if ($null -eq $app.id) {
        Write-Host "  ❌  Failed to create App Registration for $($w.WorkloadId)" -ForegroundColor Red
        $results += [pscustomobject]@{
            WorkloadId   = $w.WorkloadId
            WorkloadName = $w.WorkloadName
            AppId        = "ERROR"
            Secret       = ""
            AppIdUri     = ""
            ConsentUrl   = ""
        }
        continue
    }

    $secret = ""
    if ($CreateSecret) {
        $now        = [DateTime]::UtcNow
        $secretBody = @{
            passwordCredential = @{
                displayName = "WorkloadSecret"
                startDateTime = $now.ToString('u') -replace ' ', 'T'
                endDateTime   = $now.AddDays(180).ToString('u') -replace ' ', 'T'
            }
        } | ConvertTo-Json -Compress -Depth 10

        $secretResult = Invoke-GraphPost `
            -Url "https://graph.microsoft.com/v1.0/applications/$($app.id)/addPassword" `
            -Body $secretBody
        $secretObj = $secretResult | ConvertFrom-Json
        $secret = if ($null -ne $secretObj.secretText) { $secretObj.secretText } else { "ERROR — add manually" }
    }

    Write-Host "  ✅  App ID : $($app.appId)" -ForegroundColor Green

    $results += [pscustomobject]@{
        WorkloadId   = $w.WorkloadId
        WorkloadName = $w.WorkloadName
        AppId        = $app.appId
        Secret       = $secret
        AppIdUri     = $appIdUri
        ConsentUrl   = "https://login.microsoftonline.com/$TenantId/adminconsent?client_id=$($app.appId)"
        PortalUrl    = "https://ms.portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Overview/appId/$($app.appId)/isMSAApp~/false"
    }
}

# ── Summary ───────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  ✅  App Registrations created" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "  Copy these values into the workload env.example files:" -ForegroundColor Yellow
Write-Host ""

foreach ($r in $results) {
    Write-Host "  ┌─ $($r.WorkloadId)" -ForegroundColor Cyan
    Write-Host "  │  WorkloadName  : $($r.WorkloadName)" -ForegroundColor White
    Write-Host "  │  FRONTEND_APPID: $($r.AppId)" -ForegroundColor White
    if ($r.Secret) {
        Write-Host "  │  Client Secret : $($r.Secret)" -ForegroundColor White
    }
    Write-Host "  │  AppId URI     : $($r.AppIdUri)" -ForegroundColor DarkGray
    Write-Host "  │  Portal        : $($r.PortalUrl)" -ForegroundColor DarkGray
    Write-Host "  └─ Admin Consent : $($r.ConsentUrl)" -ForegroundColor DarkGray
    Write-Host ""
}

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Paste each FRONTEND_APPID into its workload's config\env.example (and .env.prod)"
Write-Host "  2. Grant admin consent using the URLs above (tenant admin required)"
Write-Host "  3. Run  .\scripts\Build\BuildWorkload.ps1 -Workload <id> -Environment prod"
Write-Host ""

# Return structured results for pipeline use
return $results
