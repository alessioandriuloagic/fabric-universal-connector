<#
.SYNOPSIS
    Generates requirements.lock from requirements.txt using pip-compile inside Docker.
    Run this after any change to backend/requirements.txt to keep the lockfile in sync.

.DESCRIPTION
    Uses the same python:3.11-slim image as the Dockerfile to avoid OS-level
    dependency differences. The resulting requirements.lock is committed to the repo
    and used by the Dockerfile for reproducible builds.

.EXAMPLE
    .\scripts\Build\Generate-RequirementsLock.ps1
#>

$backendDir = Join-Path $PSScriptRoot "..\..\backend"
$backendDir = (Resolve-Path $backendDir).Path

Write-Host "Generating requirements.lock from backend/requirements.txt..." -ForegroundColor Cyan

docker run --rm `
    -v "${backendDir}:/backend" `
    python:3.11-slim `
    sh -c "pip install pip-tools --quiet && pip-compile /backend/requirements.txt -o /backend/requirements.lock --no-header --quiet"

if ($LASTEXITCODE -eq 0) {
    Write-Host "requirements.lock generated successfully at backend/requirements.lock" -ForegroundColor Green
    Write-Host "Commit the lockfile: git add backend/requirements.lock && git commit -m 'chore: update requirements.lock'"
} else {
    Write-Host "Failed to generate requirements.lock (exit code $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}
