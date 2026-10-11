@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
cd /d "%~dp0"

title VideoAnalyzer - Full Setup ^& Installer

echo =====================================================================
echo          VideoAnalyzer - Full Setup ^& Dependency Installer
echo =====================================================================
echo.

:: 1. Locate Node & FFmpeg in WinGet / Program Files if not already in PATH
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Packages" (
    for /d /r "%LOCALAPPDATA%\Microsoft\WinGet\Packages" %%D in (bin) do (
        if exist "%%D\ffmpeg.exe" set "PATH=%%D;!PATH!"
    )
)
if exist "%ProgramFiles%\nodejs" (
    set "PATH=%ProgramFiles%\nodejs;!PATH!"
)
if exist "%LOCALAPPDATA%\Programs\nodejs" (
    set "PATH=%LOCALAPPDATA%\Programs\nodejs;!PATH!"
)

:: -----------------------------------------------------------------------
:: Step 1: Check Python
:: -----------------------------------------------------------------------
echo [1/6] Checking Python installation...
set "PY_CMD="

python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PY_CMD=python"
) else (
    py -3.11 --version >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_CMD=py -3.11"
    ) else (
        py -3 --version >nul 2>&1
        if !errorlevel! equ 0 (
            set "PY_CMD=py -3"
        )
    )
)

if "!PY_CMD!"=="" (
    echo [WARN] Python 3.11+ not found on system PATH.
    where winget >nul 2>&1
    if !errorlevel! equ 0 (
        set /p "INSTALL_PY=Would you like to install Python 3.11 via WinGet? (Y/N): "
        if /i "!INSTALL_PY!"=="Y" (
            echo [INFO] Installing Python 3.11...
            winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements
            echo [OK] Python installed. Please re-run install.bat to refresh environment.
            pause
            exit /b 0
        )
    )
    echo [ERROR] Python 3.11+ is required.
    echo Please install Python from https://www.python.org/
    echo [NOTE] Make sure to check "Add Python to PATH" during setup.
    pause
    exit /b 1
)

for /f "tokens=*" %%V in ('!PY_CMD! --version 2^>^&1') do echo [OK] Found %%V

:: -----------------------------------------------------------------------
:: Step 2: Check Node.js & npm (Required for Remotion video rendering)
:: -----------------------------------------------------------------------
echo.
echo [2/6] Checking Node.js and npm (Remotion engine)...
node -v >nul 2>&1
if !errorlevel! neq 0 (
    echo [WARN] Node.js is not found on PATH.
    where winget >nul 2>&1
    if !errorlevel! equ 0 (
        set /p "INSTALL_NODE=Would you like to install Node.js LTS via WinGet? (Y/N): "
        if /i "!INSTALL_NODE!"=="Y" (
            echo [INFO] Installing Node.js LTS...
            winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
            if exist "%ProgramFiles%\nodejs" set "PATH=%ProgramFiles%\nodejs;!PATH!"
        )
    )
)

node -v >nul 2>&1
if !errorlevel! neq 0 (
    echo [WARN] Node.js could not be detected.
    echo Remotion video rendering requires Node.js v18+.
    echo Download and install it from https://nodejs.org/ if needed.
) else (
    for /f "tokens=*" %%V in ('node -v 2^>^&1') do echo [OK] Found Node.js %%V
)

:: -----------------------------------------------------------------------
:: Step 3: Check FFmpeg
:: -----------------------------------------------------------------------
echo.
echo [3/6] Checking FFmpeg media engine...
ffmpeg -version >nul 2>&1
if !errorlevel! neq 0 (
    echo [WARN] FFmpeg not found on PATH.
    where winget >nul 2>&1
    if !errorlevel! equ 0 (
        set /p "INSTALL_FFMPEG=Would you like to install FFmpeg via WinGet? (Y/N): "
        if /i "!INSTALL_FFMPEG!"=="Y" (
            echo [INFO] Installing FFmpeg via WinGet...
            winget install Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
            for /d /r "%LOCALAPPDATA%\Microsoft\WinGet\Packages" %%D in (bin) do (
                if exist "%%D\ffmpeg.exe" set "PATH=%%D;!PATH!"
            )
        )
    )
)

ffmpeg -version >nul 2>&1
if !errorlevel! equ 0 (
    echo [OK] FFmpeg is available and ready.
) else (
    echo [WARN] FFmpeg was not detected. Please install FFmpeg or winget install Gyan.FFmpeg
)

:: -----------------------------------------------------------------------
:: Step 4: Setup Python Virtual Environment (.venv) & Dependencies
:: -----------------------------------------------------------------------
echo.
echo [4/6] Setting up Python virtual environment (.venv)...
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating .venv...
    !PY_CMD! -m venv .venv
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo [INFO] Installing and updating Python dependencies...
.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.venv\Scripts\python.exe -m pip install -e .
if !errorlevel! neq 0 (
    echo [ERROR] Failed to install Python dependencies.
    pause
    exit /b 1
)
echo [OK] Python dependencies installed successfully.

:: -----------------------------------------------------------------------
:: Step 5: Install Remotion NPM Dependencies
:: -----------------------------------------------------------------------
echo.
echo [5/6] Installing Remotion template dependencies (templates\quiz-remotion)...
if exist "templates\quiz-remotion\package.json" (
    pushd templates\quiz-remotion
    call npm install --no-audit --no-fund
    if !errorlevel! neq 0 (
        echo [WARN] npm install encountered warnings or errors.
    ) else (
        echo [OK] Remotion dependencies installed.
    )
    popd
)

:: Ensure project asset folders exist
if not exist "outputs" mkdir outputs
if not exist "assets\backgrounds" mkdir assets\backgrounds
if not exist "assets\sfx" mkdir assets\sfx
if not exist "temp" mkdir temp

:: -----------------------------------------------------------------------
:: Step 6: Configure Environment (.env) & API Key
:: -----------------------------------------------------------------------
echo.
echo [6/6] Configuring environment settings (.env)...
if not exist ".env" (
    if exist ".env.example" (
        copy /y ".env.example" ".env" >nul
        echo [OK] Created .env from .env.example
    ) else (
        (
            echo GOOGLE_API_KEY=your_gemini_api_key_here
            echo GEMINI_MODEL=gemini-3.8-flash
            echo OUTPUT_DIR=./outputs
        ) > ".env"
        echo [OK] Created default .env
    )
)

:: Check if API key is already configured
findstr /C:"your_gemini_api_key_here" ".env" >nul 2>&1
if !errorlevel! equ 0 (
    echo.
    echo ---------------------------------------------------------------------
    echo [API KEY SETUP]
    echo To generate trivia questions and analyze humor, a Google Gemini API Key is required.
    echo Get your free key at: https://aistudio.google.com/app/apikey
    echo ---------------------------------------------------------------------
    set /p "USER_API_KEY=Enter your Gemini API Key (or press Enter to enter later): "
    if not "!USER_API_KEY!"=="" (
        powershell -Command "(Get-Content .env) -replace 'your_gemini_api_key_here', '$env:USER_API_KEY' | Set-Content .env"
        echo [OK] API Key saved to .env
    ) else (
        echo [INFO] You can set your API key anytime in the .env file.
    )
) else (
    echo [OK] .env already contains a configured API key.
)

:: -----------------------------------------------------------------------
:: Completion
:: -----------------------------------------------------------------------
echo.
echo =====================================================================
echo                [SUCCESS] Installation Complete!
echo =====================================================================
echo.
echo You can now launch VideoAnalyzer anytime by running start.bat
echo Web Dashboard will be available at: http://localhost:7860
echo.

set /p "RUN_NOW=Would you like to start VideoAnalyzer now? (Y/N): "
if /i "!RUN_NOW!"=="Y" (
    start.bat
)

exit /b 0
