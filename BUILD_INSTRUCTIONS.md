# Build Instructions

## macOS Build

**Prerequisites:**
- python.org Python 3.12 (includes Tkinter)
- Virtual environment at: `/Users/johnoshea/Documents/programming/venvs/photo-sorting`
- All dependencies installed: `pip install -r requirements.txt tkinterdnd2 pyinstaller`

**Build Command:**
```bash
cd '/Users/johnoshea/Library/CloudStorage/OneDrive-TCDGroup/0 TCD MyDocs/01. BMI Projects/96. Photo Filer'
source /Users/johnoshea/Documents/programming/venvs/photo-sorting/bin/activate
python3 -m PyInstaller --clean packaging/pyinstaller_photo_filer.spec
```

**Output:**
- Executable: `dist/PhotoFiler` (~179MB, arm64)
- Includes bundled AI model (no internet required)
- Includes icon: `packaging/icons/photo_filer.icns`

**Test:**
```bash
./dist/PhotoFiler --help
./dist/PhotoFiler --gui
```

---

## Windows Build

**Prerequisites:**
- Python 3.12 from python.org (includes Tkinter)
- Create virtual environment: `python -m venv venv`
- Activate: `venv\Scripts\activate`
- Install dependencies: `pip install -r requirements.txt tkinterdnd2 pyinstaller`

**Build Command:**
```cmd
python -m PyInstaller --clean packaging\pyinstaller_photo_filer.spec
```

**Output:**
- Executable: `dist\PhotoFiler.exe`
- Includes bundled AI model (no internet required)
- Includes icon: `packaging\icons\photo_filer.ico`

**Test:**
```cmd
dist\PhotoFiler.exe --help
dist\PhotoFiler.exe --gui
```

---

## Notes

- **Model Bundling:** The CLIP AI model (~577MB) is bundled in `packaging/models/clip-vit-base-patch32/`
- **Offline Mode:** App loads from bundled model first, only downloads if missing
- **Console Mode:** Set `console=False` in spec file for windowed-only app (no terminal)
- **Icon:** Customize by replacing files in `packaging/icons/`
- **Signing:** macOS may require notarization for distribution outside App Store

## Distribution

**macOS:**
- Copy `dist/PhotoFiler` to any Mac (arm64)
- First run may require: Right-click → Open (bypass Gatekeeper)

**Windows:**
- Copy `dist/PhotoFiler.exe` to any Windows PC
- May require Windows Defender approval on first run
