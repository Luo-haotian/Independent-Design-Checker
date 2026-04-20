@echo off
REM Batch file to run the Independent Design Checker

set PYTHON_SCRIPT=main.py
set GUI_SCRIPT=gui.py

echo ================================================
echo  Independent Design Checker (IDC)
echo  Structural Verification System using Grok API
echo ================================================
echo.

:menu
echo.
echo Select an option:
echo 1. Run with Command Line Interface (CLI)
echo 2. Run with Graphical User Interface (GUI)
echo 3. Install Dependencies
echo 4. Exit
echo.
set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" goto cli
if "%choice%"=="2" goto gui
if "%choice%"=="3" goto install
if "%choice%"=="4" goto exit

echo Invalid choice. Please enter 1, 2, 3, or 4.
goto menu

:cli
echo.
echo Running Independent Design Checker with CLI...
echo Usage: python main.py ^<pdf_file^> [--type building/temporary] [--output-dir ^<directory^>]
echo.
set /p pdf_file="Enter path to PDF file: "
if exist "%pdf_file%" (
    set /p structure_type="Enter structure type (building/temporary) [default: building]: "
    if "%structure_type%"=="" set structure_type=building
    set /p output_dir="Enter output directory [default: ./reports]: "
    if "%output_dir%"=="" set output_dir=./reports
    python %PYTHON_SCRIPT% "%pdf_file%" --type %structure_type% --output-dir "%output_dir%"
) else (
    echo Error: File does not exist: %pdf_file%
)
pause
goto menu

:gui
echo.
echo Starting Graphical User Interface...
python %GUI_SCRIPT%
pause
goto menu

:install
echo.
echo Installing dependencies...
pip install -r requirements.txt
pause
goto menu

:exit
echo.
echo Thank you for using Independent Design Checker!
pause