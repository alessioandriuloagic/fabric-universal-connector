param (
    [switch]$NoDevServer,
    [switch]$NoDevGateway,
    [switch]$NoBackend,
    [boolean]$InteractiveLogin = $true
)

& (Join-Path $PSScriptRoot "Start-Workload.ps1") `
    -Workload "sales-crm" `
    -NoDevServer:$NoDevServer `
    -NoDevGateway:$NoDevGateway `
    -NoBackend:$NoBackend `
    -InteractiveLogin $InteractiveLogin
