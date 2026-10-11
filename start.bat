@echo off
setlocal
cd /d "%~dp0"

title VideoAnalyzer - AI Shorts Generator

echo =====================================================================
echo                VideoAnalyzer - AI Shorts Generator
echo =====================================================================
echo.

:: Automatically locate and add WinGet FFmpeg to PATH
for /d /r "%LOCALAPPDATA%\Microsoft\WinGet\Packages" %%D in (bin) do (
    if exist "%%D\ffmpeg.exe" (
        set "PATH=%%D;%PATH%"
    )
)

:: Verify Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found on system PATH!
    echo Please install Python 3.11+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Setup .env if missing
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Creating .env from .env.example...
        copy /y ".env.example" ".env" >nul
    )
)

:: Ensure dependencies are ready
python -c "import fastapi, uvicorn, google.genai, pydantic, yt_dlp" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing required Python libraries...
    pip install -e .
    echo.
)

echo =====================================================================
echo [OK] Starting VideoAnalyzer Web UI...
echo URL: http://localhost:7860
echo =====================================================================
echo.

start "" "http://localhost:7860"

python -m videoanalizer

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application exited with an error.
    pause
)
