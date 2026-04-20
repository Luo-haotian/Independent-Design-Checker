@echo off
chcp 65001 >nul
title IDC - Structural Design Checker (CLI)

echo ================================================
echo Independent Design Checker (IDC) - CLI Mode
echo ================================================
echo.

REM Check if Python is available
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python not found in PATH!
    echo Please install Python 3.8+ or use the compiled .exe version
    pause
    exit /b 1
)

REM Set default values
set PDF_FILE=%1
set TYPE=building
set MODEL=
set OUTPUT=./reports

REM Parse arguments
if "%~1"=="" goto :show_help
if "%~1"=="--help" goto :show_help
if "%~1"=="/help" goto :show_help

:parse_args
if "%~1"=="" goto :run
if "%~1"=="--type" (
    set TYPE=%2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--model" (
    set MODEL=%2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--output" (
    set OUTPUT=%2
    shift
    shift
    goto :parse_args
)
shift
goto :parse_args

:run
echo Configuration:
echo   PDF File: %PDF_FILE%
echo   Type: %TYPE%
echo   Model: %MODEL%
echo   Output: %OUTPUT%
echo.

REM Build command
set CMD=python main.py "%PDF_FILE%" --type %TYPE% --output-dir "%OUTPUT%"
if not "%MODEL%"=="" set CMD=%CMD% --model %MODEL%

echo Running: %CMD%
echo.
%CMD%

if %errorlevel% neq 0 (
    echo.
    echo ================================================
    echo Analysis failed!
    echo Check idc.log for details.
    echo ================================================
) else (
    echo.
    echo ================================================
    echo Analysis completed successfully!
    echo Report saved to: %OUTPUT%
    echo ================================================
)

pause
exit /b %errorlevel%

:show_help
echo Usage: run_cli.bat ^<pdf_file^> [options]
echo.
echo Options:
echo   --type ^<building^|temporary^>  Structure type (default: building)
echo   --model ^<model_name^>          KIMI model to use
echo   --output ^<directory^>          Output directory (default: ./reports)
echo   --help                         Show this help
echo.
echo Examples:
echo   run_cli.bat "design.pdf"
echo   run_cli.bat "design.pdf" --type temporary --model moonshot-v1-32k
echo   run_cli.bat "design.pdf" --output "C:\Reports"
echo.
echo Available models:
echo   moonshot-v1-8k    (8,000 tokens max)
echo   moonshot-v1-32k   (32,000 tokens max)  ^<- Recommended
echo   moonshot-v1-128k  (128,000 tokens max)
echo.
pause
exit /b 0
