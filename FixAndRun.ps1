# Script per creare manualmente il package .nupkg
param (
    [string]$Environment = "dev"
)

Write-Host "=== Fix e Run per Fabric Workload ===" -ForegroundColor Green
Write-Host ""

# 1. Trova l'ultima cartella temporanea
Write-Host "Cercando cartella temporanea..."
$tempDirs = Get-ChildItem -Path $env:TEMP -Filter 'Fabric_Manifest_Build_*' -Directory -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending

if ($tempDirs.Count -eq 0) {
    Write-Host "Nessuna cartella temporanea trovata. Rieseguire BuildManifestPackage.ps1 prima." -ForegroundColor Red
    exit 1
}

$latestTempDir = $tempDirs[0].FullName
Write-Host "Trovata cartella: $latestTempDir" -ForegroundColor Green

# 2. Crea il .nupkg manualmente
$outputDir = "C:\Users\AlessioAndriulo\OneDrive - Agic Technology srl\Desktop\fabric-universal-connector\build\Manifest"
$outputFile = Join-Path $outputDir "ManifestPackage.nupkg"

if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

if (Test-Path $outputFile) { 
    Write-Host "Rimuovendo file esistente..."
    Remove-Item $outputFile 
}

Write-Host "Creazione ManifestPackage.nupkg..."
Compress-Archive -Path "$latestTempDir\*" -DestinationPath $outputFile -Force

if (Test-Path $outputFile) {
    $size = (Get-Item $outputFile).Length
    Write-Host "SUCCESSO: Creato $outputFile ($size bytes)" -ForegroundColor Green
} else {
    Write-Host "ERRORE: File non creato" -ForegroundColor Red
    exit 1
}

# 3. Verifica e avvia DevGateway
$devGatewayPath = "C:\Users\AlessioAndriulo\OneDrive - Agic Technology srl\Desktop\fabric-universal-connector\tools\DevGateway\Microsoft.Fabric.Workload.DevGateway.exe"
$configPath = "C:\Users\AlessioAndriulo\OneDrive - Agic Technology srl\Desktop\fabric-universal-connector\Workload\workload-dev-mode.json"

Write-Host ""
Write-Host "=== Pronto per avviare DevGateway ===" -ForegroundColor Yellow
Write-Host "File package: $outputFile"
Write-Host "Config: $configPath"
Write-Host ""
Write-Host "Puoi ora avviare manualmente:"
Write-Host "  cd 'C:\Users\AlessioAndriulo\OneDrive - Agic Technology srl\Desktop\fabric-universal-connector\tools\DevGateway'"
Write-Host "  .\Microsoft.Fabric.Workload.DevGateway.exe"
Write-Host ""
Write-Host "Oppure usare StartDevGateway.ps1"
