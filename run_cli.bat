@echo off
chcp 65001 >nul
title IDC v0.12 - Structural Design Checker (CLI)

echo ================================================
echo Independent Design Checker (IDC) - CLI Mode
echo ================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python not found in PATH!
    echo Please install Python 3.8+ or use the compiled .exe version.
    pause
    exit /b 1
)

set PDF_FILE=%1
set TYPE=building
set MODEL=
set OUTPUT=./reports

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

set CMD=python main.py "%PDF_FILE%" --type %TYPE% --output-dir "%OUTPUT%"
if not "%MODEL%"=="" set CMD=%CMD% --model %MODEL%

echo Running: %CMD%
echo.
%CMD%

if %errorlevel% neq 0 (
    echo.
    echo ================================================
    echo Analysis failed.
    echo Check idc.log for details.
    echo ================================================
) else (
    echo.
    echo ================================================
    echo Analysis completed successfully.
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
echo   --model ^<model_name^>          Grok model to use
echo   --output ^<directory^>          Output directory (default: ./reports)
echo   --help                          Show this help
echo.
echo Examples:
echo   run_cli.bat "design.pdf"
echo   run_cli.bat "design.pdf" --type temporary --model grok-4-1-fast-non-reasoning
echo   run_cli.bat "design.pdf" --output "C:\Reports"
echo.
echo Available models:
echo   grok-4-1-fast-non-reasoning   ^<- Recommended
echo   grok-4
echo   grok-4-0709
echo   grok-3
echo   grok-3-mini
echo.
pause
exit /b 0
