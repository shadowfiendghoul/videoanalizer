@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

title VideoAnalyzer - AI Shorts Generator

echo =====================================================================
echo                VideoAnalyzer - AI Shorts Generator
echo =====================================================================
echo.

:: Automatically locate and add WinGet FFmpeg and Node.js to PATH
for /d /r "%LOCALAPPDATA%\Microsoft\WinGet\Packages" %%D in (bin) do (
    if exist "%%D\ffmpeg.exe" (
        set "PATH=%%D;!PATH!"
    )
)
if exist "%ProgramFiles%\nodejs" (
    set "PATH=%ProgramFiles%\nodejs;!PATH!"
)
if exist "%LOCALAPPDATA%\Programs\nodejs" (
    set "PATH=%LOCALAPPDATA%\Programs\nodejs;!PATH!"
)

:: Check if virtual environment exists; if not, trigger installation
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Virtual environment not found. First-time setup required.
    echo [INFO] Starting automatic installer...
    echo.
    call install.bat
    if !errorlevel! neq 0 (
        echo [ERROR] Installation failed or was cancelled.
        pause
        exit /b 1
    )
)

:: Select Python binary (.venv preferred, fallback to system)
set "PY_RUN="
if exist ".venv\Scripts\python.exe" (
    set "PY_RUN=.venv\Scripts\python.exe"
) else (
    set "PY_RUN=python"
)

:: Ensure Remotion template dependencies are installed
if exist "templates\quiz-remotion\package.json" (
    if not exist "templates\quiz-remotion\node_modules" (
        echo [INFO] Installing Remotion template dependencies...
        pushd templates\quiz-remotion
        call npm install --no-audit --no-fund >nul 2>&1
        popd
    )
)

:: Setup .env if missing
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Creating .env from .env.example...
        copy /y ".env.example" ".env" >nul
    )
)

:: Ensure required directories exist
if not exist "outputs" mkdir outputs
if not exist "assets\backgrounds" mkdir assets\backgrounds
if not exist "assets\sfx" mkdir assets\sfx
if not exist "temp" mkdir temp

echo =====================================================================
echo [OK] Starting VideoAnalyzer Web UI...
echo URL: http://localhost:7860
echo =====================================================================
echo.

:: Launch browser in background
start "" "http://localhost:7860"

:: Run server process
!PY_RUN! -m videoanalizer

if !errorlevel! neq 0 (
    echo.
    echo =====================================================================
    echo [ERROR] Application stopped unexpectedly with error code !errorlevel!.
    echo Try running install.bat to repair dependencies.
    echo =====================================================================
    pause
)
