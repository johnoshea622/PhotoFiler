#!/usr/bin/env python3
"""
Sort photos and videos into YYYYMMDD subfolders based on EXIF DateTimeOriginal
(if present) or file birth time on macOS (fallback to mtime). Logs actions to CSV.

Enhanced to handle existing folders:
- Validates existing folders against YYYYMMDD format
- Consolidates photos from incorrectly named folders to root
- Processes all root photos into correct date folders

Requirements:
- Pillow for EXIF
- pillow-heif to support HEIC/HEIF (register to let Pillow open HEIC)

Usage:
  python sort_media_by_date.py [--dir "/path/to/folder"]

Notes:
- DRY_RUN switch prevents moving files; logs intended actions.
- Handles collisions by appending __1, __2, ... to filename stem.
- Skips zero-byte files and hidden/system folders.
- For videos, we don't parse metadata; use birth/mtime only.
- Keeps local timezone.
- Phase 1: Consolidates from invalid folders to root
- Phase 2: Processes root files into YYYYMMDD folders
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, Tuple

from PIL import Image, ExifTags
try:
    import pillow_heif
    pillow_heif.register_heif_opener()  # allow Pillow to open HEIC/HEIF
except Exception:
    pillow_heif = None  # continue; HEIC may fail without this

# ----- Configuration -----
DRY_RUN: bool = False  # set to True to prevent moving files (test mode)

# Media extensions to include (lowercase)
INCLUDE_EXT = {
    ".jpg", ".jpeg", ".png", ".heic", ".heif",
    ".mov", ".mp4", ".hevc", ".avi",
}

# Extensions that should be converted to JPG for Windows compatibility
CONVERT_TO_JPG = {".heic", ".heif"}

# Folders/files to skip
SKIP_DIR_NAMES = {"@eaDir"}
SKIP_FILE_NAMES = {".DS_Store"}

# Default directory (from user request)
DEFAULT_DIR = "/Users/johnoshea/Library/CloudStorage/OneDrive-TCDGroup/TCD MyDocs/01. BMI Projects/99. Autocad Tricks/Photo adjustments"

# CSV log name in the target directory
LOG_NAME = "sort_log.csv"

# Map of EXIF tag names to IDs
EXIF_TAGS_BY_NAME = {v: k for k, v in ExifTags.TAGS.items()}
DATETIMEORIGINAL_TAG = EXIF_TAGS_BY_NAME.get("DateTimeOriginal")

@dataclass
class LogRecord:
    original_path: str
    new_path: str
    method: str  # EXIF | BIRTH | MTIME | SKIP | ERROR
    timestamp_used: str


def is_hidden(p: Path) -> bool:
    name = p.name
    if not name:
        return False
    if name.startswith('.'):
        return True
    if name in SKIP_DIR_NAMES or name in SKIP_FILE_NAMES:
        return True
    return False


def is_valid_date_folder(name: str) -> bool:
    """Check if folder name matches YYYYMMDD format and is a valid date."""
    if len(name) != 8 or not name.isdigit():
        return False
    try:
        datetime.strptime(name, "%Y%m%d")
        return True
    except ValueError:
        return False


def consolidate_from_invalid_folders(root: Path, dry_run: bool) -> list[LogRecord]:
    """Move photos from incorrectly named folders to root directory."""
    logs: list[LogRecord] = []
    
    for entry in root.iterdir():
        if not entry.is_dir() or is_hidden(entry):
            continue
            
        # Check if folder name is valid YYYYMMDD format
        if is_valid_date_folder(entry.name):
            continue  # Keep valid folders as-is
            
        # Invalid folder - move all media files to root
        for media_file in entry.iterdir():
            if not media_file.is_file() or is_hidden(media_file):
                continue
            if media_file.suffix.lower() not in INCLUDE_EXT:
                continue
                
            # Resolve collision in root directory
            dst = resolve_collision(root, media_file.name)
            
            try:
                move_or_log(media_file, dst, dry_run)
                logs.append(LogRecord(
                    original_path=str(media_file),
                    new_path=str(dst),
                    method="CONSOLIDATE",
                    timestamp_used=f"moved from invalid folder: {entry.name}"
                ))
            except Exception as e:
                logs.append(LogRecord(
                    original_path=str(media_file),
                    new_path="",
                    method="ERROR",
                    timestamp_used=f"consolidation failed: {e}"
                ))
        
        # Remove empty invalid folder (only if not dry run and folder is empty)
        if not dry_run:
            try:
                if not any(entry.iterdir()):  # Check if empty
                    entry.rmdir()
                    logs.append(LogRecord(
                        original_path=str(entry),
                        new_path="",
                        method="REMOVE_FOLDER",
                        timestamp_used="removed empty invalid folder"
                    ))
            except Exception:
                pass  # Folder not empty or permission issue
    
    return logs


def iter_media_files(root: Path) -> Iterable[Path]:
    """Iterate media files in root directory only (non-recursive)."""
    for entry in root.iterdir():
        if entry.is_file():
            if is_hidden(entry):
                continue
            if entry.suffix.lower() in INCLUDE_EXT:
                yield entry


def get_birth_or_mtime_local(path: Path) -> Tuple[datetime, str]:
    """Return (local_dt, method) using macOS birth time if available, else mtime."""
    st = path.stat()
    # On macOS, st_birthtime exists; on others, AttributeError
    ts: Optional[float] = getattr(st, 'st_birthtime', None)
    if ts is None:
        ts = st.st_mtime
        method = "MTIME"
    else:
        method = "BIRTH"
    # Convert to local time
    local_dt = datetime.fromtimestamp(ts)
    return local_dt, method


def parse_exif_datetimeoriginal(path: Path) -> Optional[datetime]:
    try:
        with Image.open(path) as im:
            exif = im.getexif()
            if not exif:
                return None
            # HEIC with pillow-heif exposes EXIF similarly
            if DATETIMEORIGINAL_TAG in exif:
                raw = exif.get(DATETIMEORIGINAL_TAG)
                if isinstance(raw, bytes):
                    raw = raw.decode(errors='ignore')
                # EXIF datetime format: "YYYY:MM:DD HH:MM:SS"
                try:
                    dt = datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S")
                    return dt  # naive local
                except Exception:
                    return None
    except Exception:
        return None
    return None


def ensure_folder(root: Path, date_str: str) -> Path:
    """Create date folder. Use YYYYMMDD format (no hyphens) to match user requirement."""
    # Convert YYYY-MM-DD to YYYYMMDD format
    clean_date = date_str.replace("-", "")
    target = root / clean_date
    target.mkdir(exist_ok=True)
    return target


def convert_heic_to_jpg(heic_path: Path, quality: int = 95) -> Optional[Path]:
    """
    Convert HEIC file to JPG for Windows compatibility.
    Returns the new JPG path if successful, None if failed.
    """
    try:
        if not pillow_heif:
            print(f"Warning: Cannot convert {heic_path.name} - pillow-heif not available")
            return None
            
        # Generate JPG filename
        jpg_name = heic_path.stem + ".jpg"
        jpg_path = heic_path.parent / jpg_name
        
        # Handle name conflicts
        base_name = heic_path.stem
        counter = 1
        while jpg_path.exists():
            jpg_name = f"{base_name}_{counter}.jpg"
            jpg_path = heic_path.parent / jpg_name
            counter += 1
        
        # Convert HEIC to JPG
        with Image.open(heic_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Preserve EXIF data if available
            exif_dict = None
            if hasattr(img, 'getexif'):
                exif_dict = img.getexif()
            
            save_kwargs = {
                'format': 'JPEG',
                'quality': quality,
                'optimize': True
            }
            
            if exif_dict:
                save_kwargs['exif'] = exif_dict
            
            img.save(jpg_path, **save_kwargs)
        
        print(f"  Converted {heic_path.name} → {jpg_path.name}")
        return jpg_path
        
    except Exception as e:
        print(f"  Error converting {heic_path.name}: {e}")
        return None


def resolve_collision(target_dir: Path, filename: str) -> Path:
    """Return a non-colliding path by appending _1, _2, ... if needed."""
    candidate = target_dir / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    i = 1
    while True:
        candidate = target_dir / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def move_or_log(src: Path, dst: Path, dry_run: bool) -> None:
    if dry_run:
        return
    try:
        # Ensure destination directory exists
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.replace(dst)
    except Exception as e:
        print(f"ERROR: Failed to move {src.name} -> {dst}: {e}")
        raise


def process_file(root: Path, path: Path) -> LogRecord:
    # Skip zero bytes
    if path.stat().st_size == 0:
        return LogRecord(str(path), "", "SKIP", "zero-bytes")

    # Convert HEIC to JPG for Windows compatibility
    original_path = path
    if path.suffix.lower() in CONVERT_TO_JPG:
        converted_path = convert_heic_to_jpg(path)
        if converted_path:
            # Use the converted JPG file for processing
            path = converted_path
            # Remove original HEIC file after successful conversion
            if not DRY_RUN:
                try:
                    original_path.unlink()
                    print(f"  Removed original: {original_path.name}")
                except Exception as e:
                    print(f"  Warning: Could not remove {original_path.name}: {e}")
        else:
            # Conversion failed, continue with original HEIC
            print(f"  Continuing with original HEIC file: {path.name}")

    method = ""
    timestamp = None

    # For videos, use birth/mtime; for images, prefer EXIF
    is_video = path.suffix.lower() in {".mov", ".mp4", ".hevc", ".avi"}
    if not is_video:
        exif_dt = parse_exif_datetimeoriginal(path)
        if exif_dt is not None:
            method = "EXIF"
            timestamp = exif_dt

    if timestamp is None:
        ts, meth = get_birth_or_mtime_local(path)
        method = meth
        timestamp = ts

    date_str = timestamp.strftime("%Y-%m-%d")
    target_dir = ensure_folder(root, date_str)
    new_name = path.name
    dst = resolve_collision(target_dir, new_name)

    move_or_log(path, dst, DRY_RUN)

    return LogRecord(
        original_path=str(original_path),
        new_path=str(dst),
        method=method if original_path == path else f"{method}_CONVERTED",
        timestamp_used=timestamp.isoformat(sep=' ', timespec='seconds'),
    )


def write_log(root: Path, rows: Iterable[LogRecord]) -> None:
    log_path = root / LOG_NAME
    first = not log_path.exists()
    with log_path.open('a', newline='') as f:
        w = csv.writer(f)
        if first:
            w.writerow(["original_path", "new_path", "method", "timestamp_used"])
        for r in rows:
            w.writerow([r.original_path, r.new_path, r.method, r.timestamp_used])


def main():
    parser = argparse.ArgumentParser(description="Sort photos/videos into YYYYMMDD folders using EXIF or file times.")
    parser.add_argument("--dir", dest="dir", default=DEFAULT_DIR, help="Directory containing media files")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Override DRY_RUN=True for a dry run")
    parser.add_argument("--no-dry-run", dest="no_dry_run", action="store_true", help="Override to actually move even if DRY_RUN=True")
    args = parser.parse_args()

    root = Path(args.dir)
    if not root.exists() or not root.is_dir():
        print(f"Directory not found: {root}")
        sys.exit(1)

    # Compute effective DRY_RUN
    dry_run = DRY_RUN
    if args.dry_run:
        dry_run = True
    if args.no_dry_run:
        dry_run = False

    print("--- Phase 1: Consolidating from invalid folders ---")
    consolidation_logs = consolidate_from_invalid_folders(root, dry_run)
    consolidated = len([log for log in consolidation_logs if log.method == "CONSOLIDATE"])
    folders_removed = len([log for log in consolidation_logs if log.method == "REMOVE_FOLDER"])
    consolidation_errors = len([log for log in consolidation_logs if log.method == "ERROR"])
    
    print(f"Photos consolidated from invalid folders: {consolidated}")
    print(f"Invalid folders removed: {folders_removed}")
    print(f"Consolidation errors: {consolidation_errors}")

    print("\n--- Phase 2: Processing root directory files ---")
    files = list(iter_media_files(root))
    total = len(files)
    moved = 0
    skipped = 0
    errors = 0
    processing_logs: list[LogRecord] = []

    for p in files:
        try:
            rec = process_file(root, p)
            processing_logs.append(rec)
            if rec.method == "SKIP":
                skipped += 1
            else:
                moved += 1
        except Exception as e:
            errors += 1
            tb = traceback.format_exc(limit=1)
            print(f"Error processing {p.name}: {e}")
            processing_logs.append(LogRecord(str(p), "", "ERROR", str(e)))

    # Combine all logs
    all_logs = consolidation_logs + processing_logs
    write_log(root, all_logs)

    print("\n--- Summary ---")
    print(f"Directory: {root}")
    print(f"DRY_RUN: {dry_run}")
    print(f"Phase 1 - Photos consolidated: {consolidated}")
    print(f"Phase 1 - Folders removed: {folders_removed}")
    print(f"Phase 2 - Root media files: {total}")
    print(f"Phase 2 - Moved (or planned): {moved}")
    print(f"Phase 2 - Skipped (zero-bytes): {skipped}")
    print(f"Total errors: {consolidation_errors + errors}")
    print(f"Log written to: {root / LOG_NAME}")


if __name__ == "__main__":
    main()
