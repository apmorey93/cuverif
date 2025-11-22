@echo off
REM Quick build script for Windows
REM Builds CuVerif Studio standalone executable

echo ============================================
echo CuVerif Studio - Windows Build Script
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Install Python from https://python.org
    pause
    exit /b 1
)

echo [1/3] Installing build dependencies...
pip install pyinstaller customtkinter --quiet

echo [2/3] Building executable...
python setup_exe.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo [3/3] Build complete!
echo.
echo Executable location:
echo   dist\CuVerif Studio\CuVerif Studio.exe
echo.
echo To create installer, open setup_installer.iss in Inno Setup
echo.
pause
