@echo off
setlocal
cd /d "%~dp0\.."

echo ============================================================
echo IDC Server Installation
echo ============================================================

where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_CMD=python"
    ) else (
        echo Python was not found. Install Python 3.10 or later, then run this installer again.
        pause
        exit /b 1
    )
)

if not exist ".venv-server" (
    %PYTHON_CMD% -m venv ".venv-server"
    if errorlevel 1 (
        echo Failed to create .venv-server.
        pause
        exit /b 1
    )
)

call ".venv-server\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip.
    pause
    exit /b 1
)
python -m pip install -r requirements_server.txt
if errorlevel 1 (
    echo Failed to install server requirements.
    pause
    exit /b 1
)

if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo Created .env from .env.example. Edit .env before production use.
) else (
    echo Existing .env found. Keeping current configuration.
)

echo.
echo Installation complete.
echo Edit .env, install Tesseract on the server, then run:
echo   server\run_server.bat
echo.
pause
