# VideoAnalyzer - PowerShell Automated Installer
[CmdletBinding()]
param(
    [switch]$SkipNpm,
    [switch]$SkipVenv,
    [string]$ApiKey
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "       VideoAnalyzer - PowerShell Setup & Dependency Installer        " -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# Locate WinGet FFmpeg if installed
$wingetPackages = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
if (Test-Path $wingetPackages) {
    Get-ChildItem -Path $wingetPackages -Filter "ffmpeg.exe" -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
        $binDir = $_.DirectoryName
        if ($env:PATH -notlike "*$binDir*") {
            $env:PATH = "$binDir;$env:PATH"
        }
    }
}
if (Test-Path "$env:ProgramFiles\nodejs") {
    if ($env:PATH -notlike "*$env:ProgramFiles\nodejs*") {
        $env:PATH = "$env:ProgramFiles\nodejs;$env:PATH"
    }
}

# 1. Check Python
Write-Host "[1/6] Checking Python installation..." -ForegroundColor Yellow
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py"
}

if (-not $pythonCmd) {
    Write-Host "[WARN] Python not found on PATH." -ForegroundColor Red
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        $ans = Read-Host "Install Python 3.11 via WinGet? (Y/N)"
        if ($ans -eq "Y" -or $ans -eq "y") {
            winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements
            Write-Host "[OK] Python installed. Please restart shell and re-run installer." -ForegroundColor Green
            exit 0
        }
    }
    Write-Host "[ERROR] Python 3.11+ is required. Install from https://www.python.org/" -ForegroundColor Red
    exit 1
}

$pyVer = & $pythonCmd --version 2>&1
Write-Host "[OK] Found $pyVer" -ForegroundColor Green

# 2. Check Node.js
Write-Host ""
Write-Host "[2/6] Checking Node.js & npm (Remotion engine)..." -ForegroundColor Yellow
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "[WARN] Node.js not detected." -ForegroundColor Yellow
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        $ans = Read-Host "Install Node.js LTS via WinGet? (Y/N)"
        if ($ans -eq "Y" -or $ans -eq "y") {
            winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
            if (Test-Path "$env:ProgramFiles\nodejs") {
                $env:PATH = "$env:ProgramFiles\nodejs;$env:PATH"
            }
        }
    }
}

if (Get-Command node -ErrorAction SilentlyContinue) {
    $nodeVer = node -v
    Write-Host "[OK] Found Node.js $nodeVer" -ForegroundColor Green
} else {
    Write-Host "[WARN] Node.js is required for Remotion video rendering (https://nodejs.org/)" -ForegroundColor Yellow
}

# 3. Check FFmpeg
Write-Host ""
Write-Host "[3/6] Checking FFmpeg media engine..." -ForegroundColor Yellow
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "[WARN] FFmpeg not found." -ForegroundColor Yellow
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        $ans = Read-Host "Install FFmpeg via WinGet? (Y/N)"
        if ($ans -eq "Y" -or $ans -eq "y") {
            winget install Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
        }
    }
}

if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    Write-Host "[OK] FFmpeg is available and ready." -ForegroundColor Green
} else {
    Write-Host "[WARN] FFmpeg is not in PATH. Some media operations may fail." -ForegroundColor Yellow
}

# 4. Setup .venv
Write-Host ""
Write-Host "[4/6] Setting up Python virtual environment (.venv)..." -ForegroundColor Yellow
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not $SkipVenv) {
    if (-not (Test-Path $venvPython)) {
        Write-Host "[INFO] Creating virtual environment .venv..." -ForegroundColor Cyan
        & $pythonCmd -m venv .venv
    }
    Write-Host "[INFO] Installing Python dependencies..." -ForegroundColor Cyan
    & $venvPython -m pip install --upgrade pip setuptools wheel --quiet
    & $venvPython -m pip install -e .
    Write-Host "[OK] Python dependencies installed." -ForegroundColor Green
}

# 5. Setup Remotion NPM
Write-Host ""
Write-Host "[5/6] Setting up Remotion template dependencies..." -ForegroundColor Yellow
if (-not $SkipNpm -and (Test-Path "templates\quiz-remotion\package.json")) {
    Push-Location "templates\quiz-remotion"
    try {
        if (Get-Command npm -ErrorAction SilentlyContinue) {
            npm install --no-audit --no-fund
            Write-Host "[OK] Remotion dependencies installed." -ForegroundColor Green
        }
    } catch {
        Write-Host "[WARN] npm install encountered an issue: $_" -ForegroundColor Yellow
    } finally {
        Pop-Location
    }
}

# Ensure asset directories
@("outputs", "assets\backgrounds", "assets\sfx", "temp") | ForEach-Object {
    if (-not (Test-Path $_)) { New-Item -ItemType Directory -Path $_ -Force | Out-Null }
}

# 6. Configure .env
Write-Host ""
Write-Host "[6/6] Configuring .env..." -ForegroundColor Yellow
$envPath = Join-Path $PSScriptRoot ".env"
$envExPath = Join-Path $PSScriptRoot ".env.example"

if (-not (Test-Path $envPath)) {
    if (Test-Path $envExPath) {
        Copy-Item $envExPath $envPath
    } else {
        Set-Content -Path $envPath -Value "GOOGLE_API_KEY=your_gemini_api_key_here`nGEMINI_MODEL=gemini-3.8-flash`nOUTPUT_DIR=./outputs"
    }
}

$envContent = Get-Content $envPath -Raw
if ($ApiKey) {
    $envContent = $envContent -replace "your_gemini_api_key_here", $ApiKey
    Set-Content -Path $envPath -Value $envContent
    Write-Host "[OK] API Key saved to .env" -ForegroundColor Green
} elseif ($envContent -like "*your_gemini_api_key_here*") {
    $keyInput = Read-Host "Enter your Google Gemini API Key (or press Enter to set later)"
    if ($keyInput) {
        $envContent = $envContent -replace "your_gemini_api_key_here", $keyInput.Trim()
        Set-Content -Path $envPath -Value $envContent
        Write-Host "[OK] API Key saved to .env" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "                [SUCCESS] Installation Complete!                    " -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "Run .\start.bat to launch VideoAnalyzer Web Dashboard." -ForegroundColor Cyan
Write-Host "URL: http://localhost:7860" -ForegroundColor Cyan
