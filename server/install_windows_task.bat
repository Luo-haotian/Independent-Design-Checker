@echo off
setlocal
cd /d "%~dp0\.."

net session >nul 2>&1
if not "%errorlevel%"=="0" (
    echo Please run this script as Administrator.
    exit /b 1
)

set TASK_NAME=IDC Server
set PROJECT_ROOT=%CD%
set "RUN_CMD=cmd.exe /c ""%PROJECT_ROOT%\server\run_server.bat"""

echo Creating Windows startup task: %TASK_NAME%
schtasks /Create /TN "%TASK_NAME%" /SC ONSTART /RU SYSTEM /RL HIGHEST /TR "%RUN_CMD%" /F

echo.
echo Task created. Start it now with:
echo   schtasks /Run /TN "%TASK_NAME%"
echo.
pause
