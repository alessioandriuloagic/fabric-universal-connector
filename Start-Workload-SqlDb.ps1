param (
    [switch]$NoDevServer,
    [switch]$NoDevGateway,
    [switch]$NoBackend,
    [boolean]$InteractiveLogin = $true
)

& (Join-Path $PSScriptRoot "Start-Workload.ps1") `
    -Workload "sql-db" `
    -NoDevServer:$NoDevServer `
    -NoDevGateway:$NoDevGateway `
    -NoBackend:$NoBackend `
    -InteractiveLogin $InteractiveLogin
