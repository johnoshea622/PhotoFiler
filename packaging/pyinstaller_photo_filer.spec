# PyInstaller spec for the Photo Filer app (macOS/Windows)

import sys
from pathlib import Path

block_cipher = None

# Resolve repo root robustly for both local and GitHub Actions paths.
spec_path = Path(SPECPATH).resolve()
spec_dir = spec_path.parent
candidates = [
    spec_dir.parent,       # .../repo
    Path.cwd().resolve(),  # current working directory
]
repo_root = None
for candidate in candidates:
    if (candidate / "master_photo_processor.py").exists():
        repo_root = candidate
        break
if repo_root is None:
    raise FileNotFoundError("Unable to locate repo root from spec file.")

script = str(repo_root / "master_photo_processor.py")

icons_dir = repo_root / "packaging/icons"
icon_mac = icons_dir / "photo_filer.icns"
icon_win = icons_dir / "photo_filer.ico"
icon_file = None
if sys.platform == "darwin" and icon_mac.exists():
    icon_file = str(icon_mac)
elif sys.platform.startswith("win") and icon_win.exists():
    icon_file = str(icon_win)

# Only bundle the PyTorch weights and tokenizer bits to keep size down.
model_dir = repo_root / "packaging/models/clip-vit-base-patch32"
model_files = [
    "README.md",
    "config.json",
    "merges.txt",
    "preprocessor_config.json",
    "pytorch_model.bin",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
]

missing_models = [name for name in model_files if not (model_dir / name).exists()]
if missing_models:
    raise FileNotFoundError(
        f"Missing model files in {model_dir}: {', '.join(missing_models)}"
    )

model_datas = [
    (str(model_dir / name), f"packaging/models/clip-vit-base-patch32/{name}")
    for name in model_files
]

a = Analysis(
    [script],
    pathex=[str(repo_root)],
    binaries=[],
    datas=model_datas,
    hiddenimports=[
        # Ensure Tk drag/drop and Pillow TK helper are bundled when present
        "tkinterdnd2",
        "PIL._tkinter_finder",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PhotoFiler",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # windowed app (no terminal)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PhotoFiler",
)

app = BUNDLE(
    coll,
    name="PhotoFiler.app",
    icon=icon_file,
    bundle_identifier="com.tcd.photofiler",
)
