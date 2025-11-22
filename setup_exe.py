"""
Setup script for building CuVerif Windows executable
====================================================
Creates standalone .exe using PyInstaller

Usage:
    python setup_exe.py
    
This will create:
    dist/CuVerif Studio.exe    - Standalone executable
    dist/CuVerif Studio/       - Folder with all dependencies
"""

import os
import subprocess
import sys

def build_exe():
    """Build Windows executable using PyInstaller."""
    
    print("=" * 70)
    print("Building CuVerif Studio Windows Executable")
    print("=" * 70)
    
    # Check PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("\nERROR: PyInstaller not installed")
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--name=CuVerif Studio",
        "--onedir",  # Create folder with dependencies
        "--windowed",  # No console window
        "--icon=NONE",  # TODO: Add icon file
        "--add-data=README.md;.",
        "--add-data=QUICKSTART.md;.",
        "--hidden-import=customtkinter",
        "--hidden-import=numba",
        "--hidden-import=numpy",
        "src/cuverif_studio.py"
    ]
    
    print("\nRunning PyInstaller...")
    print(" ".join(cmd))
    print()
    
    try:
        subprocess.check_call(cmd)
        print("\n" + "=" * 70)
        print("SUCCESS! Executable created:")
        print("  dist/CuVerif Studio/CuVerif Studio.exe")
        print("=" * 70)
        print("\nTo create an installer, run: setup_installer.iss with Inno Setup")
        
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_exe()
