@echo off
setlocal
cd /d "%~dp0\.."

echo ============================================================
echo IDC Server Installation
echo ============================================================

if not exist ".venv-server" (
    py -3 -m venv ".venv-server"
)

call ".venv-server\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements_server.txt

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
