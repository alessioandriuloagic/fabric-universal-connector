@echo off
REM Quick setup for running the workload without PowerShell 7+
REM This script:
REM 1. Installs npm dependencies
REM 2. Builds the manifest package
REM 3. Prepares for starting DevGateway and DevServer

echo ====================================
echo Fabric Universal Connector - Setup
echo ====================================
echo.

REM Check if Node.js is installed
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

echo [1/3] Installing npm dependencies...
cd /d "%~dp0Workload"
if exist package.json (
    call npm install
    if %errorlevel% neq 0 (
        echo ERROR: npm install failed
        pause
        exit /b 1
    )
) else (
    echo ERROR: package.json not found
    pause
    exit /b 1
)

echo.
echo [2/3] Building manifest package...
cd /d "%~dp0"
if exist scripts\Build\BuildManifestPackage.ps1 (
    powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\Build\BuildManifestPackage.ps1" -Environment "dev"
    if %errorlevel% neq 0 (
        echo ERROR: Manifest build failed
        pause
        exit /b 1
    )
) else (
    echo ERROR: BuildManifestPackage.ps1 not found
    pause
    exit /b 1
)

echo.
echo [3/3] Setup complete!
echo.
echo ====================================
echo Next steps:
echo ====================================
echo.
echo 1. Open a new Command Prompt and run:
echo    cd scripts\Run
echo    StartDevGateway.ps1
echo.
echo 2. Open another Command Prompt and run:
echo    cd scripts\Run
echo    StartDevServer.ps1
echo.
echo Then go to http://localhost:3000 or http://localhost:5173
echo.
pause
