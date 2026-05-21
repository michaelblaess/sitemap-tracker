# Sitemap Tracker - Windows Installer
# Usage: irm https://raw.githubusercontent.com/michaelblaess/sitemap-tracker/main/install.ps1 | iex

$ErrorActionPreference = "Stop"
$Repo = "michaelblaess/sitemap-tracker"
$InstallDir = "$env:LOCALAPPDATA\sitemap-tracker"

Write-Host "=== Sitemap Tracker - Installer ===" -ForegroundColor Cyan
Write-Host ""

# Neuestes Release von GitHub holen
Write-Host "Suche neuestes Release..."
$Release = Invoke-RestMethod "https://api.github.com/repos/$Repo/releases/latest"
$Version = $Release.tag_name

# Windows Asset finden (versionsunabhaengig per Teilstring)
$Asset = $Release.assets |
    Where-Object { $_.name -like '*-windows-*.zip' } |
    Select-Object -First 1
if (-not $Asset) {
    Write-Host "  [FEHLER] Kein Windows-Asset im Release gefunden!" -ForegroundColor Red
    Write-Host "  Verfuegbare Assets:"
    $Release.assets | ForEach-Object { Write-Host "    $($_.name)" }
    exit 1
}

Write-Host "Version: $Version"
Write-Host "Download: $($Asset.browser_download_url)"

# Altes Verzeichnis entfernen
if (Test-Path $InstallDir) {
    Remove-Item $InstallDir -Recurse -Force
}
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

# Herunterladen
Write-Host "Lade herunter..."
$TmpFile = Join-Path $env:TEMP "sg-installer.zip"
Invoke-WebRequest -Uri $Asset.browser_download_url -OutFile $TmpFile

# Entpacken
Write-Host "Entpacke..."
Expand-Archive -Path $TmpFile -DestinationPath $InstallDir -Force
Remove-Item $TmpFile -Force

# Wenn Dateien in einem Unterordner liegen, eine Ebene hochziehen
$SubDirs = Get-ChildItem $InstallDir -Directory
if ($SubDirs.Count -eq 1) {
    $SubDir = $SubDirs[0].FullName
    Get-ChildItem $SubDir | Move-Item -Destination $InstallDir -Force
    Remove-Item $SubDir -Force -ErrorAction SilentlyContinue
}

# Zum User-PATH hinzufuegen
$UserPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($UserPath -notlike "*$InstallDir*") {
    Write-Host "Fuege $InstallDir zum PATH hinzu..."
    [Environment]::SetEnvironmentVariable("PATH", "$InstallDir;$UserPath", "User")
    $env:PATH = "$InstallDir;$env:PATH"
}

Write-Host ""
Write-Host "Installation abgeschlossen!" -ForegroundColor Green
Write-Host ""
Write-Host "Starten mit: sitemap-tracker https://example.com"
Write-Host ""
Write-Host "HINWEIS: Neues Terminal oeffnen damit PATH-Aenderung wirkt." -ForegroundColor Yellow
