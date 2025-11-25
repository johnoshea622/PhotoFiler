#!/usr/bin/env python3
"""
HEIC to JPG Converter for Windows Compatibility

Converts HEIC/HEIF files to high-quality JPG format while preserving EXIF metadata.
Designed for better compatibility with Windows 11 and various applications.

Features:
- Maintains original EXIF data (creation time, GPS, camera settings)
- High-quality JPG output (95% quality by default)
- Batch processing with progress tracking
- Dry-run mode for testing
- Detailed conversion logging
- Handles file name collisions automatically

Usage:
  python heic_converter.py [--dir "/path/to/photos"] [--quality 95] [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, ExifTags
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIF_AVAILABLE = True
except ImportError:
    HEIF_AVAILABLE = False
    print("Warning: pillow-heif not available. Install with: pip install pillow-heif")

# Configuration
DEFAULT_DIR = "/Users/johnoshea/Library/CloudStorage/OneDrive-TCDGroup/0 TCD MyDocs/01. BMI Projects/99. Autocad Tricks/Photo adjustments/input photos"
DEFAULT_QUALITY = 95  # JPG quality (1-100, 95 is very high quality)
DRY_RUN = False

# File extensions
HEIC_EXTENSIONS = {".heic", ".heif"}
LOG_NAME = "heic_conversion_log.csv"


def is_heic_file(file_path: Path) -> bool:
    """Check if file is HEIC/HEIF format."""
    return file_path.suffix.lower() in HEIC_EXTENSIONS


def get_jpg_output_path(heic_path: Path) -> Path:
    """Generate JPG output path, handling name conflicts."""
    jpg_name = heic_path.stem + ".jpg"
    jpg_path = heic_path.parent / jpg_name
    
    # Handle name conflicts by appending numbers
    counter = 1
    while jpg_path.exists():
        jpg_name = f"{heic_path.stem}_{counter}.jpg"
        jpg_path = heic_path.parent / jpg_name
        counter += 1
    
    return jpg_path


def convert_heic_to_jpg(heic_path: Path, quality: int = DEFAULT_QUALITY, dry_run: bool = False) -> Dict:
    """
    Convert a single HEIC file to JPG while preserving EXIF data.
    
    Returns:
        Dict with conversion results including success status, paths, and metadata
    """
    result = {
        "original_path": str(heic_path),
        "converted_path": "",
        "success": False,
        "error": "",
        "file_size_before": 0,
        "file_size_after": 0,
        "exif_preserved": False
    }
    
    if not HEIF_AVAILABLE:
        result["error"] = "pillow-heif not available"
        return result
    
    try:
        # Get original file size
        result["file_size_before"] = heic_path.stat().st_size
        
        # Generate output path
        jpg_path = get_jpg_output_path(heic_path)
        result["converted_path"] = str(jpg_path)
        
        if dry_run:
            result["success"] = True
            result["file_size_after"] = result["file_size_before"]  # Estimate
            return result
        
        # Open and convert HEIC image
        with Image.open(heic_path) as img:
            # Convert to RGB if needed (HEIC can be in other color spaces)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Preserve EXIF data
            exif_dict = None
            if hasattr(img, '_getexif') and img._getexif() is not None:
                exif_dict = img._getexif()
            elif hasattr(img, 'getexif'):
                exif_dict = img.getexif()
            
            # Save as JPG with high quality
            save_kwargs = {
                'format': 'JPEG',
                'quality': quality,
                'optimize': True
            }
            
            # Include EXIF if available
            if exif_dict:
                save_kwargs['exif'] = exif_dict
                result["exif_preserved"] = True
            
            img.save(jpg_path, **save_kwargs)
        
        # Get converted file size
        result["file_size_after"] = jpg_path.stat().st_size
        result["success"] = True
        
    except Exception as e:
        result["error"] = str(e)
        result["success"] = False
    
    return result


def process_directory(directory: Path, quality: int = DEFAULT_QUALITY, dry_run: bool = False) -> List[Dict]:
    """Process all HEIC files in a directory."""
    
    if not directory.exists() or not directory.is_dir():
        print(f"Directory not found: {directory}")
        return []
    
    # Find all HEIC files
    heic_files = []
    for ext in HEIC_EXTENSIONS:
        heic_files.extend(directory.glob(f"*{ext}"))
        heic_files.extend(directory.glob(f"*{ext.upper()}"))
    
    if not heic_files:
        print("No HEIC files found to convert")
        return []
    
    print(f"Found {len(heic_files)} HEIC files to convert")
    if dry_run:
        print("DRY RUN MODE - No files will actually be converted")
    
    results = []
    
    for i, heic_file in enumerate(heic_files, 1):
        print(f"[{i}/{len(heic_files)}] Converting {heic_file.name}...")
        
        result = convert_heic_to_jpg(heic_file, quality, dry_run)
        results.append(result)
        
        if result["success"]:
            if dry_run:
                print(f"  → Would convert to: {Path(result['converted_path']).name}")
            else:
                size_before = result["file_size_before"] / 1024 / 1024  # MB
                size_after = result["file_size_after"] / 1024 / 1024   # MB
                print(f"  ✓ Converted to: {Path(result['converted_path']).name}")
                print(f"    Size: {size_before:.1f}MB → {size_after:.1f}MB")
                if result["exif_preserved"]:
                    print(f"    EXIF data preserved")
        else:
            print(f"  ✗ Failed: {result['error']}")
    
    return results


def write_conversion_log(results: List[Dict], log_path: Path) -> None:
    """Write detailed conversion log to CSV."""
    with log_path.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", "original_file", "converted_file", "success", 
            "size_before_mb", "size_after_mb", "exif_preserved", "error"
        ])
        
        for result in results:
            original_name = Path(result["original_path"]).name
            converted_name = Path(result["converted_path"]).name if result["converted_path"] else ""
            size_before_mb = result["file_size_before"] / 1024 / 1024
            size_after_mb = result["file_size_after"] / 1024 / 1024
            
            writer.writerow([
                datetime.now().isoformat(),
                original_name,
                converted_name,
                result["success"],
                f"{size_before_mb:.2f}",
                f"{size_after_mb:.2f}",
                result.get("exif_preserved", False),
                result.get("error", "")
            ])


def cleanup_heic_files(results: List[Dict], dry_run: bool = False) -> None:
    """
    Optionally remove original HEIC files after successful conversion.
    Only removes files that were successfully converted.
    """
    successful_conversions = [r for r in results if r["success"]]
    
    if not successful_conversions:
        return
    
    print(f"\nCleanup: Found {len(successful_conversions)} successfully converted HEIC files")
    
    if dry_run:
        print("DRY RUN MODE - Would remove original HEIC files:")
        for result in successful_conversions:
            print(f"  Would remove: {Path(result['original_path']).name}")
        return
    
    response = input("Remove original HEIC files after successful conversion? (y/N): ")
    
    if response.lower() in ['y', 'yes']:
        removed_count = 0
        for result in successful_conversions:
            try:
                original_path = Path(result["original_path"])
                original_path.unlink()
                print(f"  ✓ Removed: {original_path.name}")
                removed_count += 1
            except Exception as e:
                print(f"  ✗ Failed to remove {original_path.name}: {e}")
        
        print(f"Removed {removed_count} original HEIC files")
    else:
        print("Original HEIC files kept")


def main():
    parser = argparse.ArgumentParser(description="Convert HEIC files to JPG for Windows compatibility")
    parser.add_argument("--dir", default=DEFAULT_DIR, help="Directory containing HEIC files")
    parser.add_argument("--quality", type=int, default=DEFAULT_QUALITY, 
                       help="JPG quality (1-100, default: 95)")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be converted without actually converting")
    parser.add_argument("--cleanup", action="store_true", 
                       help="Remove original HEIC files after successful conversion")
    args = parser.parse_args()
    
    if not HEIF_AVAILABLE:
        print("Error: pillow-heif is required but not installed")
        print("Install with: pip install pillow-heif")
        sys.exit(1)
    
    directory = Path(args.dir)
    
    # Validate quality setting
    if not 1 <= args.quality <= 100:
        print("Quality must be between 1 and 100")
        sys.exit(1)
    
    print(f"HEIC to JPG Converter")
    print(f"Directory: {directory}")
    print(f"Quality: {args.quality}%")
    print(f"Dry run: {args.dry_run}")
    print("-" * 50)
    
    # Process files
    results = process_directory(directory, args.quality, args.dry_run)
    
    if not results:
        return
    
    # Write log
    log_path = directory / LOG_NAME
    write_conversion_log(results, log_path)
    
    # Summary
    total_files = len(results)
    successful = sum(1 for r in results if r["success"])
    failed = total_files - successful
    
    total_size_before = sum(r["file_size_before"] for r in results) / 1024 / 1024
    total_size_after = sum(r["file_size_after"] for r in results) / 1024 / 1024
    
    print(f"\n--- Conversion Summary ---")
    print(f"Total HEIC files: {total_files}")
    print(f"Successfully converted: {successful}")
    print(f"Failed: {failed}")
    print(f"Total size before: {total_size_before:.1f}MB")
    print(f"Total size after: {total_size_after:.1f}MB")
    
    if successful > 0:
        compression_ratio = (total_size_after / total_size_before) * 100
        print(f"Size ratio: {compression_ratio:.1f}% of original")
    
    print(f"Log file: {log_path}")
    
    # Optional cleanup
    if args.cleanup and successful > 0:
        cleanup_heic_files(results, args.dry_run)


if __name__ == "__main__":
    main()