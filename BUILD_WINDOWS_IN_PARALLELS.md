# Building Windows Executable in Parallels

Since this project folder is in OneDrive, it should be accessible from your Windows VM in Parallels.

## Steps in Windows VM

### 1. Access the Project Folder
The OneDrive folder should be synced and accessible in Windows at:
```
C:\Users\YourWindowsUsername\OneDrive - TCD Group\0 TCD MyDocs\01. BMI Projects\96. Photo Filer
```

### 2. Install Python 3.12 for Windows
- Download from: https://www.python.org/downloads/windows/
- **Important:** Choose "Windows installer (64-bit)"
- During installation, check "Add Python to PATH"
- Verify: Open Command Prompt and type `python --version`

### 3. Create Virtual Environment
```cmd
cd "C:\Users\YourWindowsUsername\OneDrive - TCD Group\0 TCD MyDocs\01. BMI Projects\96. Photo Filer"
python -m venv venv-windows
venv-windows\Scripts\activate
```

### 4. Install Dependencies
```cmd
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install tkinterdnd2 pyinstaller
```

### 5. Build the Executable
```cmd
python -m PyInstaller --clean --noconfirm packaging\pyinstaller_photo_filer.spec
```

This will take 5-10 minutes and create:
- `dist\PhotoFiler.exe` (~1.3GB with bundled AI model)

### 6. Test the Executable
```cmd
dist\PhotoFiler.exe --help
dist\PhotoFiler.exe
```

The GUI should open automatically (no --gui flag needed).

## What Gets Built

- **Standalone .exe** - No Python or dependencies needed on target Windows PCs
- **Bundled AI Model** - Works offline, no internet required
- **Icon** - Uses `packaging/icons/photo_filer.ico`
- **Size** - ~1.3GB (includes PyTorch, transformers, and CLIP model)

## Troubleshooting

### "Python not found"
- Reinstall Python and check "Add to PATH" during installation
- Or add manually: `C:\Users\YourName\AppData\Local\Programs\Python\Python312`

### "Module not found" errors
- Make sure you activated the venv: `venv-windows\Scripts\activate`
- Check you're in the project root directory

### Build fails with memory error
- Close other applications to free RAM
- Allocate more memory to Parallels VM (recommend 8GB+)

### Tkinter import errors
- Make sure you installed Python from python.org, not from Windows Store
- Python.org version includes Tkinter by default

## Distribution

Once built, copy `dist\PhotoFiler.exe` to any Windows PC. It's completely standalone.

**Note:** Windows Defender may flag it on first run (common for PyInstaller apps). Users need to click "More info" → "Run anyway".
