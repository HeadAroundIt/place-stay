# Build a Windows installer for Place. Stay.
# Requires Inno Setup 6 (ISCC.exe) and Python 3.

param(
    [switch]$SkipFreeze
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $PSScriptRoot

function Find-ISCC {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
    )
    foreach ($path in $candidates) {
        if ($path -and (Test-Path $path)) {
            return $path
        }
    }
    $fromPath = Get-Command iscc -ErrorAction SilentlyContinue
    if ($fromPath) {
        return $fromPath.Source
    }
    throw "Inno Setup 6 was not found. Install it from https://jrsoftware.org/isinfo.php then run this again."
}

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Creating virtual environment..."
    py -3 -m venv .venv
    $python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
}

Write-Host "Installing Python packages..."
& $python -m pip install --disable-pip-version-check -q -r requirements.txt pyinstaller

Write-Host "Drawing icons and installer art..."
& $python (Join-Path $PSScriptRoot "installer\prepare_assets.py")
if ($LASTEXITCODE -ne 0) { throw "Asset generation failed." }

if (-not $SkipFreeze) {
    Write-Host "Freezing Place. Stay..."
    & $python -m PyInstaller (Join-Path $PSScriptRoot "PlaceStay.spec") --noconfirm --clean
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }
}

$distExe = Join-Path $PSScriptRoot "dist\PlaceStay\PlaceStay.exe"
if (-not (Test-Path $distExe)) {
    throw "Frozen app not found at $distExe"
}

Write-Host "Compiling installer..."
$iscc = Find-ISCC
& $iscc (Join-Path $PSScriptRoot "installer\PlaceStay.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compile failed." }

$outDir = Join-Path $PSScriptRoot "installer\out"
$setup = Get-ChildItem $outDir -Filter "PlaceStay-*-Setup.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $setup) {
    throw "Installer was not written to $outDir"
}

Write-Host ""
Write-Host "Installer ready:"
Write-Host "  $($setup.FullName)"
