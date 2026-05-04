@echo off
setlocal
cd /d "%~dp0\.."

if not exist ".venv-server\Scripts\activate.bat" (
    echo Server virtual environment not found. Run server\install_server.bat first.
    pause
    exit /b 1
)

call ".venv-server\Scripts\activate.bat"

if "%IDC_SERVER_HOST%"=="" set IDC_SERVER_HOST=0.0.0.0
if "%IDC_SERVER_PORT%"=="" set IDC_SERVER_PORT=8080

echo IDC server starting at http://%IDC_SERVER_HOST%:%IDC_SERVER_PORT%
python server\idc_server.py
pause
