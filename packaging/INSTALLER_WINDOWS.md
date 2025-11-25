Windows Installer (Inno Setup)
==============================

This builds a standard Windows installer (PhotoFiler-Setup.exe) from the PyInstaller output.

Prereqs (on Windows)
1) Build the app with PyInstaller so `dist\PhotoFiler.exe` exists. Easiest: run `build-windows.bat` from the project root (uses python.org Python, bundles the offline CLIP model).
2) Install Inno Setup (includes `iscc.exe`): https://jrsoftware.org/isinfo.php

Build steps
1) Open a Windows Command Prompt in the project root.
2) Build the executable if not already present:
   ```
   build-windows.bat
   ```
   Result: `dist\PhotoFiler.exe`
3) Run Inno Setup compiler:
   ```
   iscc packaging\windows_installer.iss
   ```
   Result: `PhotoFiler-Setup.exe` in the project root (or the Inno Setup output folder).

What the installer does
- Installs to `{localappdata}\Programs\PhotoFiler` (no admin needed).
- Adds Start Menu shortcut; optional desktop shortcut.
- Copies the PyInstaller-built EXE (includes the offline model and GUI).

Notes
- Installer size will be large (~1GB+) because the offline CLIP model is bundled in the EXE.
- If you rebuild the app, rerun `iscc` to refresh the installer.
