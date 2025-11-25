Packaging TODO
=============

Goal: ship standalone executables for macOS and Windows using PyInstaller (keeps changes minimal and works with the existing Tk GUI).

Status / tasks
- [x] Pick packager and add a spec file (PyInstaller spec added at packaging/pyinstaller_photo_filer.spec).
- [x] Document build commands for macOS and Windows.
- [x] Add app icon and wire it into the spec (see packaging/icons).
- [x] Bundle CLIP model for offline use (packaging/models/clip-vit-base-patch32) and load with local_files_only when present.
- [x] Build and smoke-test macOS app from the python.org Python (includes Tk) with your venv dependencies installed.
  - ✅ Built successfully: `dist/PhotoFiler` (arm64) with icon
  - ✅ CLI tested: `./dist/PhotoFiler --help`
  - ☐ GUI smoke-test via built binary (pending manual run)
- [ ] Build and smoke-test Windows app from the python.org 64-bit Python with the same deps installed.
- [ ] Adjust defaults for packaged runs if needed (e.g., default input/output paths, log locations).
- [ ] Add version metadata.
- [ ] Code signing / notarization (per platform, optional).

Prereqs
- Use the python.org installers so Tk is bundled. Verify with `python3 -m tkinter`.
- Install dependencies in a venv: `pip install -r requirements.txt pillow-heif tkinterdnd2`.
- Install PyInstaller: `pip install pyinstaller`.
- Models: the CLIP model is pre-downloaded at `packaging/models/clip-vit-base-patch32` and is bundled by the spec. If you need to refresh, run:  
  `python - <<'PY'\nfrom huggingface_hub import snapshot_download\nfrom pathlib import Path\nsnapshot_download('openai/clip-vit-base-patch32', local_dir=Path('packaging/models/clip-vit-base-patch32'), local_dir_use_symlinks=False)\nPY`

Build commands
- macOS (from repo root):
  - `python3 -m PyInstaller --clean packaging/pyinstaller_photo_filer.spec`
  - Outputs: `dist/PhotoFiler` (console app) and `build/` artifacts.
  - Run the built app: `./dist/PhotoFiler --gui` (use the GUI) or with CLI flags as usual.
- Windows (from repo root, in a cmd or PowerShell with the venv active):
  - `python -m PyInstaller --clean packaging\\pyinstaller_photo_filer.spec`
  - Outputs: `dist\\PhotoFiler.exe`.

Notes
- Drag-and-drop requires `tkinterdnd2` in the build environment; PyInstaller will bundle it if present.
- The spec keeps `console=True` so the executable can be used via CLI and shows logs; change to `console=False` in the spec if you want a pure windowed app.
- If pillow-heif is absent, HEIC conversion will be skipped at runtime (same as now).
- Icons live at `packaging/icons/photo_filer.icns` (mac) and `packaging/icons/photo_filer.ico` (win). The spec auto-picks based on platform.
