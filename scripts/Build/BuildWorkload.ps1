param (
    # Target workload to build
    [ValidateSet("customer-insight-journey", "sales-crm", "business-central", "sql-db")]
    [string]$Workload = "customer-insight-journey",

    # Fabric workload name — must match WorkloadManifest.xml registration
    # e.g. "Org.CustomerInsightJourney"
    [string]$WorkloadName,

    # Entra App Registration ID for THIS workload's frontend (one per workload)
    [string]$FrontendAppId,

    # Shared backend App Registration ID (same for all workloads)
    [string]$BackendAppId,

    # Semantic version for the manifest NuGet package
    [string]$WorkloadVersion,

    # Target environment
    [ValidateSet("dev", "test", "prod")]
    [string]$Environment = "prod"
)

Set-StrictMode -Off
$ErrorActionPreference = "Stop"

$repoRoot          = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$workloadDir       = Join-Path $repoRoot "workloads\$Workload"
$workloadConfigFile= Join-Path $workloadDir "config\workload.json"
$workloadManifestDir = Join-Path $workloadDir "manifest"
$sharedAssetsDir   = Join-Path $repoRoot "Workload\Manifest\assets"
$frontendDir       = Join-Path $repoRoot "Workload"
$releaseDir        = Join-Path $repoRoot "release\$Workload"
$manifestOutputDir = Join-Path $repoRoot "build\$Workload\Manifest"
$frontendBuildDir  = Join-Path $repoRoot "build\Frontend"

Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Fabric Workload Build — $Workload ($Environment)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $workloadConfigFile)) {
    Write-Error "Workload config not found: $workloadConfigFile"
    exit 1
}
$workloadConfig = Get-Content $workloadConfigFile -Raw | ConvertFrom-Json
Write-Host "  Workload : $($workloadConfig.displayName)" -ForegroundColor White
Write-Host "  Source   : $($workloadConfig.source)" -ForegroundColor White
Write-Host ""

# ── 1. Merge env vars (base → workload override → CLI params) ────────

$envVars = @{}

$baseEnvFile = Join-Path $frontendDir ".env.$Environment"
if (Test-Path $baseEnvFile) {
    Get-Content $baseEnvFile | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') { $envVars[$matches[1].Trim()] = $matches[2].Trim() }
    }
    Write-Host "  Loaded base env     : $baseEnvFile" -ForegroundColor DarkGray
}

$workloadEnvFile = Join-Path $workloadDir "config\.env.$Environment"
if (Test-Path $workloadEnvFile) {
    Get-Content $workloadEnvFile | ForEach-Object {
        if ($_ -match '^([^#=]+)=(.*)$') { $envVars[$matches[1].Trim()] = $matches[2].Trim() }
    }
    Write-Host "  Loaded workload env : $workloadEnvFile" -ForegroundColor DarkGray
} else {
    Write-Host "  ⚠️  No workload env file at $workloadEnvFile — using base env only." -ForegroundColor Yellow
}

# CLI overrides take highest priority
if ($WorkloadName)    { $envVars['WORKLOAD_NAME']     = $WorkloadName }
if ($FrontendAppId)   { $envVars['FRONTEND_APPID']    = $FrontendAppId }
if ($BackendAppId)    { $envVars['BACKEND_APPID']     = $BackendAppId }
if ($WorkloadVersion) { $envVars['WORKLOAD_VERSION']  = $WorkloadVersion }

# These are always set by the build script — not overridable by env files
$envVars['REACT_APP_WORKLOAD_ID'] = $Workload
$envVars['ITEM_NAMES']            = 'Connector'

Write-Host ""
Write-Host "  Effective config:" -ForegroundColor DarkGray
Write-Host "    WORKLOAD_NAME            = $($envVars['WORKLOAD_NAME'])" -ForegroundColor DarkGray
Write-Host "    WORKLOAD_VERSION         = $($envVars['WORKLOAD_VERSION'])" -ForegroundColor DarkGray
Write-Host "    FRONTEND_APPID           = $($envVars['FRONTEND_APPID'])" -ForegroundColor DarkGray
Write-Host "    FRONTEND_URL             = $($envVars['FRONTEND_URL'])" -ForegroundColor DarkGray
Write-Host "    REACT_APP_WORKLOAD_ID    = $($envVars['REACT_APP_WORKLOAD_ID'])" -ForegroundColor DarkGray
Write-Host ""

# ── 2. Build manifest NuGet ──────────────────────────────────────────

Write-Host "Step 1/3 — Building manifest NuGet..." -ForegroundColor Yellow

$guid     = [Guid]::NewGuid().ToString()
$tempPath = Join-Path ([System.IO.Path]::GetTempPath()) "FabricWorkload_${Workload}_$guid"
New-Item -ItemType Directory -Path $tempPath -Force | Out-Null

if (-not (Test-Path $manifestOutputDir)) {
    New-Item -ItemType Directory -Path $manifestOutputDir -Force | Out-Null
}
$manifestOutputDir = (Resolve-Path $manifestOutputDir).Path

# Copy workload-specific manifest templates
Copy-Item -Path "$workloadManifestDir\*" -Destination $tempPath -Recurse -Force

# Merge shared assets (icons/images) — workload assets take precedence if present
if (Test-Path $sharedAssetsDir) {
    $sharedAssetsTarget = Join-Path $tempPath "assets"
    if (-not (Test-Path $sharedAssetsTarget)) {
        New-Item -ItemType Directory -Path $sharedAssetsTarget -Force | Out-Null
    }
    # Copy shared first, then workload-specific (if any) overwrite
    Copy-Item -Path "$sharedAssetsDir\*" -Destination $sharedAssetsTarget -Recurse -Force
    Write-Host "  Merged shared assets from Workload\Manifest\assets\" -ForegroundColor DarkGray
    $workloadAssetsDir = Join-Path $workloadDir "manifest\assets"
    if (Test-Path $workloadAssetsDir) {
        Copy-Item -Path "$workloadAssetsDir\*" -Destination $sharedAssetsTarget -Recurse -Force
        Write-Host "  Merged workload-specific assets" -ForegroundColor DarkGray
    }
}

# Flatten items/* into root (required by NuGet packaging)
$itemsPath = Join-Path $tempPath "items"
if (Test-Path $itemsPath) {
    $itemFiles = Get-ChildItem -Path $itemsPath -Recurse -Include "*.json","*.xml"
    foreach ($f in $itemFiles) {
        $dest = Join-Path $tempPath $f.Name
        if (Test-Path $dest) {
            $prefix = Split-Path (Split-Path $f.FullName -Parent) -Leaf
            $dest   = Join-Path $tempPath "$prefix$($f.Name)"
        }
        Move-Item -Path $f.FullName -Destination $dest
    }
}

# Replace {{PLACEHOLDER}} in all template files
$filesToProcess = Get-ChildItem -Path $tempPath -Recurse -Include "*.xml","*.json","*.nuspec"
foreach ($file in $filesToProcess) {
    $content  = Get-Content $file.FullName -Raw -Encoding UTF8
    $original = $content
    foreach ($key in $envVars.Keys) {
        $content = $content -replace [regex]::Escape("{{$key}}"), $envVars[$key]
    }
    $content = $content -replace '\{\{WORKLOAD_ID\}\}',      $envVars['WORKLOAD_NAME']
    $content = $content -replace [regex]::Escape('{{MANIFEST_FOLDER}}'), $tempPath
    if ($content -ne $original) {
        Set-Content -Path $file.FullName -Value $content -Encoding UTF8
    }
}

# Pack NuGet
$nugetPath  = Join-Path $frontendDir "node_modules\nuget-bin\nuget.exe"
$nuspecPath = Join-Path $tempPath "ManifestPackage.nuspec"

if (-not (Test-Path $nugetPath)) {
    Write-Host "  nuget.exe not found — running npm install in Workload/..." -ForegroundColor Yellow
    Push-Location $frontendDir
    try { npm install } finally { Pop-Location }
}

$onWindows = $IsWindows -or ($PSVersionTable.PSVersion.Major -lt 6 -and [System.Environment]::OSVersion.Platform -eq 'Win32NT')
if ($onWindows) {
    & $nugetPath pack $nuspecPath -OutputDirectory $manifestOutputDir -Verbosity quiet
} else {
    mono $nugetPath pack $nuspecPath -OutputDirectory $manifestOutputDir -Verbosity quiet
}

if ($LASTEXITCODE -ne 0) { Write-Error "nuget pack failed."; exit 1 }
Write-Host "  ✅ Manifest NuGet: $manifestOutputDir" -ForegroundColor Green

# ── 3. Build frontend ────────────────────────────────────────────────

Write-Host ""
Write-Host "Step 2/3 — Building frontend..." -ForegroundColor Yellow
Write-Host "  npm script : build:$Workload`:$Environment" -ForegroundColor DarkGray

Push-Location $frontendDir
try {
    npm run "build:${Workload}:${Environment}"
    if ($LASTEXITCODE -ne 0) { Write-Error "Frontend build failed."; exit 1 }
} finally {
    Pop-Location
}
Write-Host "  ✅ Frontend built" -ForegroundColor Green

# ── 4. Assemble release directory ────────────────────────────────────

Write-Host ""
Write-Host "Step 3/3 — Assembling release..." -ForegroundColor Yellow

if (Test-Path $releaseDir) { Remove-Item -Path $releaseDir -Recurse -Force }
New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null

Move-Item -Path "$manifestOutputDir\*.nupkg" -Destination $releaseDir -Force

$releaseAppDir = Join-Path $releaseDir "app"
New-Item -ItemType Directory -Path $releaseAppDir -Force | Out-Null
if (Test-Path $frontendBuildDir) {
    Copy-Item -Path "$frontendBuildDir\*" -Destination $releaseAppDir -Recurse -Force
}

# Cleanup temp
if (Test-Path $tempPath) { Remove-Item $tempPath -Recurse -Force -ErrorAction SilentlyContinue }

# ── Summary ──────────────────────────────────────────────────────────

Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  ✅  $($workloadConfig.displayName) — release ready" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "  Manifest NuGet  : $releaseDir\*.nupkg" -ForegroundColor Cyan
Write-Host "  Frontend bundle : $releaseAppDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Upload NuGet to Fabric Admin Portal -> Workloads -> Upload package"
Write-Host "  2. Deploy frontend:"
Write-Host "     .\scripts\Deploy\DeployToStaticWebApp.ps1 \"
Write-Host "       -AppName <your-swa-name> \"
Write-Host "       -ResourceGroupName <rg> \"
Write-Host "       -ReleasePath ..\..\release\$Workload\app"
Write-Host ""
