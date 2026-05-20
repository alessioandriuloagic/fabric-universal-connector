param (
    [ValidateSet("universal", "customer-insight-journey", "sales-crm", "business-central", "sql-db")]
    [string]$Workload = "universal"
)

################################################
# Starting the DevServer
################################################
Write-Host ""
Write-Host "Starting the DevServer (workload: $Workload)..."
$devServerdDir = Join-Path $PSScriptRoot "..\..\Workload"
Push-Location $devServerdDir
try {
    if ($env:CODESPACES -eq "true") {
        Write-Host "Running in Codespace environment - using low memory configuration to prevent OOM errors"
        $env:NODE_ENV = "codespace"
        npm run start:codespace
    } elseif ($Workload -eq "universal") {
        npm start
    } else {
        npm run "start:$Workload"
    }
} finally {
    Pop-Location
}
