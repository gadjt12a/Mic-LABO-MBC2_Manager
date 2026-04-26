@echo off
title MBC2 Dashboard
echo ================================================
echo   MBC2 Dashboard - mic-LABO Motor Boot Camp 2
echo ================================================
echo.

REM Kill any existing process using port 8766
REM Use findstr to get the PID, filter out PID 0 (System Idle)
echo Checking for existing server on port 8766...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr /R ":8766 "') do (
    if not "%%a"=="0" (
        if not "%%a"=="PID" (
            echo Killing existing process PID: %%a
            taskkill /F /PID %%a >nul 2>&1
        )
    )
)

REM Small delay to let port release
timeout /t 2 /nobreak >nul

REM Check for Python and launch
if exist "%~dp0python-bundle\python.exe" (
    echo Starting with bundled Python...
    "%~dp0python-bundle\python.exe" "%~dp0server.py"
    goto end
)

python --version >nul 2>&1
if %errorlevel% == 0 (
    echo Starting server...
    echo.
    python "%~dp0server.py"
    goto end
)

python3 --version >nul 2>&1
if %errorlevel% == 0 (
    echo Starting server...
    echo.
    python3 "%~dp0server.py"
    goto end
)

echo ERROR: Python not found.
echo Please install Python from https://python.org/downloads
echo.
pause

:end
