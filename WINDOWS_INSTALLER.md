# Building Windows Installer for CuVerif Studio

## Quick Start (Simple)

### Build Standalone .exe

```bash
# Install build tools
pip install pyinstaller

# Build executable
python setup_exe.py
```

This creates: `dist/CuVerif Studio/CuVerif Studio.exe`

**To run**: Double-click the .exe file

---

## Professional Installer (Advanced)

### Prerequisites

1. **Build the .exe first** (see above)
2. **Install Inno Setup**: Download from https://jrsoftware.org/isinfo.php

### Build Installer

1. Open `setup_installer.iss` in Inno Setup Compiler
2. Click "Compile" 
3. Output: `installers/CuVerif_Studio_Setup.exe`

### Features

- ✅ Desktop shortcut
- ✅ Start menu entry  
- ✅ Uninstaller
- ✅ Professional wizard UI
- ✅ No Python installation required

---

## Manual Build Steps

### 1. Install Dependencies

```bash
pip install pyinstaller customtkinter
```

### 2. Build with PyInstaller

```bash
pyinstaller --name="CuVerif Studio" ^
  --onedir ^
  --windowed ^
  --hidden-import=customtkinter ^
  --hidden-import=numba ^
  src/cuverif_studio.py
```

### 3. Test the Executable

```bash
cd dist/"CuVerif Studio"
"CuVerif Studio.exe"
```

---

## Troubleshooting

### "Missing module" errors

Add to `setup_exe.py`:
```python
"--hidden-import=module_name",
```

### .exe is too large

Use `--onefile` instead of `--onedir` (creates single 100MB+ file)

### CUDA not working

CUDA requires driver installed on target machine. CPU backend always works.

### Antivirus blocking

PyInstaller executables sometimes trigger false positives. Sign the .exe or whitelist.

---

## Distribution

**Simple**:
- ZIP the `dist/CuVerif Studio/` folder
- Users extract and run `CuVerif Studio.exe`

**Professional**:
- Build installer with Inno Setup
- Distribute `CuVerif_Studio_Setup.exe`
- Users run installer, get Start menu entry + desktop shortcut

---

## Requirements for Users

- **Windows 10/11** (64-bit)
- **No Python required** (bundled in .exe)
- **Optional**: NVIDIA GPU with CUDA for GPU backend

---

*Last Updated: 2025-11-21*
