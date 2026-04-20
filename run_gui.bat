@echo off
chcp 65001 >nul
title IDC v0.11 - Structural Design Checker (GUI)

echo Starting IDC GUI...
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python not found in PATH!
    echo Please install Python 3.8+ or use IDC_GUI.exe
    pause
    exit /b 1
)

python gui.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: GUI failed to start.
    echo Check idc.log for details.
    pause
)

exit /b %errorlevel%
